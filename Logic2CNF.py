from SymbolicLogic import *
from myutils import *
import string
import subprocess
import hashlib
import os
import pickle

import pdb

class Logic2CNF(SymbolicLogic):
    def __init__(self, stateProp, flops=[]):
        SymbolicLogic.__init__(self, stateProp, flops)
        self.__l2cnf = "/home/kkelley/Downloads/logic2cnf-0.7.2/logic2cnf"
        self.__cnf = dict()
        #self.__cnfmap = dict()
        self.__re = re.compile("c\s+\|\s+(\d+) = (\S+)")

        # clear any old files at start
        #for st in range(len(flops)):
        #    fname = self.__cnffile__(st)
        #    if os.path.exists(fname):
        #        os.remove(fname)
        #    fname = self.__cnfmapfile__(st)
        #    if os.path.exists(fname):
        #        os.remove(fname)

        precompute=False
        if precompute:
            raise Exception("This is deprecated")
            for st in range(len(flops)):
                # find CNF
                self.__cnf[st] = self.__cnf__(st, False)
                # find Map
                #self.__cnfmap[st] = self.__cnfmap__(self.__cnf[st])
    
    def fileHeader(self):
        inputs = self.cleanNames(string.join(self.inputs()))
        return "def "  + inputs + ";\n"

    def fileBody(self, state, constraints=True):
        if constraints:
            output = applyAnd([self.getOutLogic(state), self.getInLogic()])
        else:
            output = self.getOutLogic(state)

        output = self.cleanNames(output)
        output = self.convertOps(output)
        return output + ";\n"

    def cleanNames(self, string):
        string = re.sub("\[", "_", string)
        string = re.sub("\]", "_", string)
        string = re.sub("\.", "_", string)
        string = string.lower()
        return string

    def convertOps(self, string):
        string = re.sub("&",  ".", string)
        string = re.sub("\|", "+", string)
        string = re.sub("!",  "~", string)
        return string

    def cnffile(self, state, constraints=True):
        "Returns the name of a CNF file, creates it if missing"
        fname = self.__cnffile__(state)

        # create the cnf file if it doesn't exist
        if not os.path.exists(fname):
            cnf = self.__cnf__(state, constraints)
            newfd = os.open(fname, os.O_EXCL | os.O_CREAT | os.O_RDWR)
            f = os.fdopen(newfd, 'w') 
            f.write(cnf)
            f.close()
        
        return fname

    def __cnffile__(self, state):
        f ="/tmp/cnf"+hashlib.sha224(str(self.outputs())+str(state)).hexdigest()
        return f


    def cnf(self, state, constraints=True):
        raise Exception("Trying to deprecate this function")
        # Cache the CNF string if we're ignoring constraints
        if constraints or not (state in self.__cnf):
            cnf = self.__cnf__(state, constraints)
        else:
            cnf = self.__cnf[state]

        # save this cnf for next time
        self.__cnf[state] = cnf

        return cnf
       

    def __cnf__(self, state, constraints):
        l2cnf = subprocess.Popen([self.__l2cnf, "-c"], 
                                 stdin=subprocess.PIPE, 
                                 stdout=subprocess.PIPE)
        logic = self.fileHeader() + self.fileBody(state, constraints)
        return l2cnf.communicate(logic)[0]


    def cnfmap(self, state):
        fname = self.__cnfmapfile__(state)
        if os.path.exists(fname):
            f = open(fname, 'rb')
            thismap = pickle.load(f)

        else:
            thismap = self.__cnfmap__(self.cnffile(state, False))
            f = open(fname, 'wb')
            pickle.dump(thismap, f, pickle.HIGHEST_PROTOCOL)

        return thismap
        #if state not in self.__cnfmap:
        #    self.__cnfmap[state] = self.__cnfmap__(self.cnffile(state, False))
        #return self.__cnfmap[state]

    def __cnfmapfile__(self, state):
        f ="/tmp/map"+hashlib.sha224(str(self.outputs())+str(state)).hexdigest()
        return f

    def __cnfmap__(self, cnffile):
        "Parse CNF comments, build map of input name -> number"
        #print "Internal findCNFMap function called"

        mapping = dict()

        # read CNF file into cnf
        f = open(cnffile, 'r')
        cnf = f.readlines()
        f.close()

        #cnf = string.split(cnf, "\n")
        inputs = map(self.cleanNames, self.inputs())
        
        for line in cnf:
            if len(line) > 0 and line[0] == "c":
                m = self.__re.match(line)
                if m:
                    if m.group(2) in inputs:
                        mapping[m.group(2)] = m.group(1)
        return mapping


    def assumptions(self, state):
        """
        Produces a DNF-like file listing the input assumptions per line
        Uses mapping as dict to map between input names and output numbers
        """
        fname = self.__assumpfile__(state)

        # ALWAYS create new assumption files
        mapping = self.cnfmap(state)
        output = ""
        states = self.state()
        for state in states.states:
            stateStr = states.getStateStr(state)
            nodes = map(self.cleanNames, states.nodes())
            nodes = map(mapping.get, nodes)
            inv = map(applyInvChar, list(stateStr), ["-"]*len(stateStr))
            tmp = map(lambda x,y:str(x)+str(y), inv, nodes)
            output += reduce(lambda x,y:x + " " + y, tmp) + " 0\n"

        f = open(fname, 'w') 
        f.write(output)
        f.close()
        return fname

    def __assumpfile__(self, state):
        f ="/tmp/assump"+hashlib.sha224(str(self.outputs())+str(state)).hexdigest()
        return f
