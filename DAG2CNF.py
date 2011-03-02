from SymbolicLogic import *
from myutils import *
#from odict import OrderedDict
import string
import subprocess
import hashlib
import os
import pickle

import pdb


class DAG2CNF:
    def __init__(self, stateProp, flops=[]):

        if len(flops) == 0:
            flops = stateProp.defaultFlops()

        if "TMPDIR" in os.environ:
            self.__tmp = os.environ["TMPDIR"]
        else:
            self.__tmp = "/tmp"

        inputs = set()
        for flop in flops:
            inputs = set.union(inputs, stateProp.deps[flop])
        inputs = list(inputs)
        inputs.sort()
        inputs.reverse()
        
        self.__flops  = flops
        self.__inputs = inputs
        
        self.__getLogic__(stateProp)

        # not sure if this is still needed (copied verbatim from SymbolicLogic)
        self.setState(stateProp.state)


    def __getLogic__(self, stateProp):
        # create map to number all nodes by visiting all nodes once
        #self.__nodemap = OrderedDict()
        self.__nodemap = dict()
        for flop in self.__flops:
            self.__touchNode__(stateProp, flop)
        
        # now create CNF clauses for each node using these numberings
        self.__touched = dict()
        self.__cnf     = ""
        self.__comment = ""
        for node in self.__nodemap:
            self.__comment += "c |\t" + str(self.__nodemap[node]) + " = "+node+"\n"
        self.__tmpnum  = len(self.__nodemap)+1
        for flop in self.__flops:
            self.__getCNFNode__(stateProp, flop)


    def __touchNode__(self, stateProp, node):
        if not node in self.__nodemap:
            dag = stateProp.dag
            self.__nodemap[node] = len(self.__nodemap)+1
            if dag.isInput(node):
                return
            for prev in dag.node_incidence[node]:
                self.__touchNode__(stateProp, prev)

    def __getCNFNode__(self, stateProp, node):
        if not node in self.__touched:
            dag = stateProp.dag
            lib = stateProp.lib
            nl  = stateProp.nl

            # base case: return name if it's a circuit input
            if dag.isInput(node):
                return

            # otherwise find name mappings for this node's inputs and
            # find CNF logic
            inps = dict()
            for prev in dag.node_incidence[node]:
                for pin in dag.pins((prev,node))[1]:
                    inps[pin] = self.__nodemap[prev]
            name = nl.mods[nl.topMod].cells[node].submodname
            if len(inps) != len(lib.inputs[name]):
                raise Exception("Not enough inputs on " + node)
            inps['out'] = self.__nodemap[node]

            lib.py2cnf[name].getCNF(inps, self.__tmpnum)
            self.__cnf += lib.py2cnf[name].cnf
            #self.__comment += lib.py2cnf[name].comment
            self.__tmpnum += lib.py2cnf[name].tmpvars
            self.__touched[node] = True

            # call recursively on predecessors
            for prev in dag.node_incidence[node]:
                self.__getCNFNode__(stateProp, prev)


    def setState(self, state):
        constInputs = list(set.intersection(set(state.nodes()), 
                                            set(self.__inputs)))
        constInputs.sort()
        constInputs.reverse()
        self.__state  = State.subset(state, constInputs)

    def state(self):
        return self.__state

    def inputs(self):
        return self.__inputs

    def outputs(self):
        return self.__flops

    def cnffile(self, state, constraints=False):
        "Returns the name of a CNF file, creates it if missing"
        fname = self.__cnffile__(state)

        # create the cnf file if it doesn't exist
        if not os.path.exists(fname):
            cnf = self.__comment + self.__cnf + self.__cnf__(state)
            newfd = os.open(fname, os.O_EXCL | os.O_CREAT | os.O_RDWR)
            f = os.fdopen(newfd, 'w') 
            f.write(cnf)
            f.close()
        
        return fname

    def __cnffile__(self, state):
        f =self.__tmp + "/cnf" +hashlib.sha224(str(self.outputs())+str(state)).hexdigest()
        return f


    def __cnf__(self, state):
        """ produces the state-specific portion of the cnf file"""
        if state >= 2**len(self.__flops):
            raise Exception("Invalid state " + str(state))
        stateStr = bin(state)[2:].rjust(len(self.__flops), '0')
        cnf = ""
        for i in range(len(self.__flops)):
            invchar = ""
            if stateStr[i] == "0":
                invchar = "-"

            cnf += invchar + str(self.__nodemap[self.__flops[i]]) + " 0\n"
        return cnf

    #def cnfmap(self, state):
    #    fname = self.__cnfmapfile__(state)
    #    if os.path.exists(fname):
    #        f = open(fname, 'rb')
    #        thismap = pickle.load(f)
    #
    #    else:
    #        thismap = self.__cnfmap__(self.cnffile(state, False))
    #        f = open(fname, 'wb')
    #        pickle.dump(thismap, f, pickle.HIGHEST_PROTOCOL)
    #
    #    return thismap
    #    #if state not in self.__cnfmap:
    #    #    self.__cnfmap[state] = self.__cnfmap__(self.cnffile(state, False))
    #    #return self.__cnfmap[state]
    #
    #def __cnfmapfile__(self, state):
    #    f =self.__tmp +"/map"+hashlib.sha224(str(self.outputs())+str(state)).hexdigest()
    #    return f
    #
    #def __cnfmap__(self, cnffile):
    #    "Parse CNF comments, build map of input name -> number"
    #    #print "Internal findCNFMap function called"
    #
    #    mapping = dict()
    #
    #    # read CNF file into cnf
    #    f = open(cnffile, 'r')
    #    cnf = f.readlines()
    #    f.close()
    #
    #    #cnf = string.split(cnf, "\n")
    #    inputs = map(self.cleanNames, self.inputs())
    #    
    #    for line in cnf:
    #        if len(line) > 0 and line[0] == "c":
    #            m = self.__re.match(line)
    #            if m:
    #                if m.group(2) in inputs:
    #                    mapping[m.group(2)] = m.group(1)
    #    return mapping


    def assumptions(self, state):
        """
        Produces a DNF-like file listing the input assumptions per line
        Uses mapping as dict to map between input names and output numbers
        """
        fname = self.__assumpfile__(state)

        # ALWAYS create new assumption files
        #mapping = self.cnfmap(state)
        mapping = self.__nodemap
        #output = ""
        f = open(fname, 'w') 
        states = self.state()
        for state in states.states:
            stateStr = states.getStateStr(state)
            nodes = states.nodes()
            nodes = map(mapping.get, nodes)
            inv = map(applyInvChar, list(stateStr), ["-"]*len(stateStr))
            tmp = map(lambda x,y:str(x)+str(y), inv, nodes)
            #output += reduce(lambda x,y:x + " " + y, tmp) + " 0\n"
            f.write(reduce(lambda x,y:x + " " + y, tmp) + " 0\n")
        f.close()
        return fname

    def __assumpfile__(self, state):
        f =self.__tmp + "/assump"+hashlib.sha224(str(self.outputs())+str(state)).hexdigest()
        return f