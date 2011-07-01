from SymbolicLogic import *
from myutils import *
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
        
        self.__design = stateProp.nl.topMod
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
            name = dag.node2module(node)
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
        #constInputs = list(set.intersection(set(state.nodes()), 
        #                                    set(self.__inputs)))
        #constInputs.sort()
        #constInputs.reverse()
        #self.__state  = state.subset(constInputs)
        self.__state = state

    def state(self):
        return self.__state

    def inputs(self):
        return self.__inputs

    def setOutputs(self, outputs):
        self.__flops = outputs

    def outputs(self):
        return self.__flops

    def cnffile(self, force=False):
        "Returns the name of a CNF file, creates it if missing"
        fname = self.__cnffile__()

        if force and os.path.exists(fname):
            os.remove(fname)

        # create the cnf file if it doesn't exist
        if not os.path.exists(fname):
            cnf = self.__comment + self.__cnf
            newfd = os.open(fname, os.O_EXCL | os.O_CREAT | os.O_RDWR)
            f = os.fdopen(newfd, 'w') 
            f.write(cnf)
            f.close()
        
        return fname

    def __cnffile__(self):
        f =self.__tmp + "/cnf" + self.__design
        return f


    def __cnf__(self, state, dnf=False):
        """ produces the state-specific portion of the cnf file"""
        if state >= 2**len(self.outputs()):
            raise Exception("Invalid state " + str(state))
        cnf = ""

        if dnf:
            endStr = " "
        else:
            endStr = " 0\n"

        for i in range(len(self.outputs())):
            if not state & (1 << (len(self.outputs())-1-i)):
                cnf += "-"
            cnf += str(self.__nodemap[self.outputs()[i]]) + endStr

        if dnf:
            cnf += "0\n"
        return cnf


    def assumptionsIn(self):
        """
        Produces a DNF-like file listing the input assumptions per line
        Uses mapping as dict to map between input names and output numbers
        """
        froot   = self.__assumpfile__(0, False)
        #mapping = self.__nodemap
        states = self.state()
        #nodes    = states.nodes()
        #nodeNums = map(mapping.get, nodes)

        fnames = []
        for grp in states.states():
            state = states.states()[grp]
            if not state.full():
                idx = 0
                for sub in state.subgroups():
                    fname = froot+ "." +str(grp)+ "." +str(idx)
                    self.__writeGrpAssumptions__(fname, sub)
                    idx += 1
                    fnames.append(fname)

        #f = open(fname, 'w')
        #outStr = ''
        #for state in states.states:
        #    for i in range(len(nodes)):
        #        if not states.getState(state, nodes[i]):
        #            outStr += '-'
        #        outStr += str(nodeNums[i]) + ' '
        #    outStr += " 0\n"
        #f.write(outStr)
        #f.close()

        return fnames


    def __writeGrpAssumptions__(self, fname, states):
        mapping  = self.__nodemap
        nodes    = states.nodes()
        nodeNums = map(mapping.get, nodes)

        f = open(fname, 'w')
        outStr = ''
        for state in states.states:
            for i in range(len(nodes)):
                if not states.getState(state, nodes[i]):
                    outStr += '-'
                outStr += str(nodeNums[i]) + ' '
            outStr += " 0\n"
        f.write(outStr)
        f.close()


    def assumptionsOutGroup(self, states, groups=1):
        fnames = []
        stateGroups = []
        if len(states) < groups:
            groups = len(states)

        nPerGroup = (len(states) / groups) + (len(states) % groups)
        for i in range(groups):
            fname = self.__assumpfile__(i, True)
            f = open(fname, 'w')

            stateGroup = []
            for j in range(i*nPerGroup,min(len(states),(i+1)*nPerGroup)):
            #for state in states:
                f.write(self.__cnf__(states[j], dnf=True))
                stateGroup.append(states[j])
            f.close()
            fnames.append(fname)
            stateGroups.append(stateGroup)
        return (fnames, stateGroups)

    def assumptionsOut(self, states):
        fnames = []
        for state in states:
            fname = self.__assumpfile__(state, True)
            fnames.append(fname)
            f = open(fname, 'w')
            f.write(self.__cnf__(state, dnf=True))
            f.close()
        return fnames


    def __assumpfile__(self, state, out=True):
        if out:
            typeStr = "Out"
        else:
            typeStr = "In"
        f =self.__tmp + "/assump"+typeStr+hashlib.sha224(str(self.outputs())+str(state)+str(out)).hexdigest()
        return f
