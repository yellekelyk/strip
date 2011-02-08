from SymbolicLogic import *
from myutils import *
import string
import subprocess

import pdb

class Logic2CNF(SymbolicLogic):
    def __init__(self, stateProp, flops=[], precompute=False):
        SymbolicLogic.__init__(self, stateProp, flops)
        self.__l2cnf = "/home/kkelley/Downloads/logic2cnf-0.7.2/logic2cnf"
        self.__cnf = dict()
        self.__cnfmap = dict()
        self.__re = re.compile("c\s+\|\s+(\d+) = (\S+)")

        if precompute:
            for st in range(len(flops)):
                # find CNF
                self.__cnf[st] = self.__cnf__(st, False)
                # find Map
                self.__cnfmap[st] = self.__cnfmap__(self.__cnf[st])
    
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

    #def cnfExists(self, state):
    #    return state in self.__cnf
    #
    #def forceCNF(self, state, cnf):
    #    self.__cnf[state] = cnf

    def cnf(self, state, constraints=True):
        # Cache the CNF string if we're ignoring constraints
        if constraints or not (state in self.__cnf):
            cnf = self.__cnf__(state, constraints)
        else:
            cnf = self.__cnf[state]

        # save this cnf for next time
        self.__cnf[state] = cnf

        # only save !constraints calls!
        #if (not constraints):
        #    self.__cnf[state] = cnf

        return cnf
       

    def __cnf__(self, state, constraints):
        #print "Internal compute CNF function called, state=" + str(state) + " constraints=" + str(constraints)

        l2cnf = subprocess.Popen([self.__l2cnf, "-c"], 
                                 stdin=subprocess.PIPE, 
                                 stdout=subprocess.PIPE)
        logic = self.fileHeader() + self.fileBody(state, constraints)
        return l2cnf.communicate(logic)[0]


    def cnfmap(self, state):
        #pdb.set_trace()
        if state not in self.__cnfmap:
            self.__cnfmap[state] = self.__cnfmap__(self.cnf(state, False))
        return self.__cnfmap[state]


    def __cnfmap__(self, cnf):
        "Parse CNF comments, build map of input name -> number"
        #print "Internal findCNFMap function called"

        mapping = dict()
        cnf = string.split(cnf, "\n")
        inputs = map(self.cleanNames, self.inputs())
        
        for line in cnf:
            if len(line) > 0 and line[0] == "c":
                m = self.__re.match(line)
                if m:
                    if m.group(2) in inputs:
                        mapping[m.group(2)] = m.group(1)
        return mapping


    #def getCNFMap(self, state):
    #    if state not in self.__cnfmap:
    #        self.__cnfmap[state] = self.__cnfmap__(self.cnf(state, False))
    #    return self.__cnfmap[state]

    #def forceMap(self, state, cnfMap):
    #    self.__cnfmap[state] = cnfMap

    def assumptions(self, state):
        """
        Produces a DNF-like file listing the input assumptions per line
        Uses mapping as dict to map between input names and output numbers
        """
        mapping = self.cnfmap(state)
        #pdb.set_trace()

        output = ""
        states = self.state()
        for state in states.states:
            stateStr = states.getStateStr(state)
            nodes = map(self.cleanNames, states.nodes())
            nodes = map(mapping.get, nodes)
            inv = map(applyInvChar, list(stateStr), ["-"]*len(stateStr))
            tmp = map(lambda x,y:str(x)+str(y), inv, nodes)
            output += reduce(lambda x,y:x + " " + y, tmp) + " 0\n"
        return output


