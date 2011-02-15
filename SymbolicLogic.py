import re
from myutils import *
import State

import pdb

class SymbolicLogic:
    "A class for manpiulating Symbolic Boolean Logic"
    def __init__(self, stateProp, flops):
        if len(flops) == 0:
            flops = stateProp.defaultFlops()

        inputs = set()
        for flop in flops:
            inputs = set.union(inputs, stateProp.deps[flop])
        inputs = list(inputs)
        inputs.sort()
        inputs.reverse()
        
        self.__flops  = flops
        self.__inputs = inputs

        #self.__logic  = stateProp.logic
        self.__logic = self.__getLogic__(stateProp)
        
        #self.__state = stateProp.getInputState

        self.setState(stateProp.state)
        #constInputs = set.intersection(set(stateProp.state.nodes()),
        #                               set(inputs))
        #constInputs = list(constInputs)
        #constInputs.sort()
        #constInputs.reverse()
        #self.__state  = State.subset(stateProp.state, constInputs)

    def __getLogic__(self, stateProp):
        logic = dict()
        cache = dict()
        for flop in self.__flops:
            logic[flop] = self.__getLogicNode__(stateProp, flop, cache)
        return logic

    def __getLogicNode__(self, stateProp, node, cache):
        if not node in cache:
            dag = stateProp.dag
            lib = stateProp.lib
            nl  = stateProp.nl

            # base case: return name if it's a circuit input
            if dag.isInput(node):
                return node

            # otherwise find sim logic for each predecessor, evaluate
            # for this node, and return
            inps = dict()
            for prev in dag.node_incidence[node]:
                for pin in dag.pins((prev,node))[1]:
                    inps[pin] = self.__getLogicNode__(stateProp, prev, cache)
            name = nl.mods[nl.topMod].cells[node].submodname
            if len(inps) != len(lib.inputs[name]):
                raise Exception("Not enough inputs on " + node)

            # construct arguments in order
            argList = []
            for arg in lib.inputs[name]:
                argList.append(inps[arg])

            cache[node] = lib.logic[name](*argList)
        return(cache[node])




    def inputs(self):
        return self.__inputs

    def outputs(self):
        return self.__flops

    def setState(self, state):
        constInputs = list(set.intersection(set(state.nodes()), 
                                            set(self.__inputs)))
        constInputs.sort()
        constInputs.reverse()
        self.__state  = State.subset(state, constInputs)

    #def state(self):
    #    st = self.__state()
    #    constInputs = list(set.intersection(set(st.nodes()),
    #                                        set(self.__inputs)))
    #    constInputs.sort()
    #    constInputs.reverse()
    #    return State.subset(st, constInputs)

    def state(self):
        return self.__state

    def toFile(self, fileName, state):
        f = open(fileName, 'w')
        f.write(self.fileHeader())
        f.write(self.fileBody(state))
        f.close()

    def cnf(self, state):
        raise Exception("Should be implemented by child!")

    #def cleanNames(self, string):
    #    pass
    
    #def convertOps(self, string):
    #    pass

    #def toCNFFile(self, fileName, state, partialEval=False):
    #    raise Exception("Not implemented")
    #
    #    if partialEval:
    #        inputs = list(set.difference(set(self.__inputs), 
    #                                     self.__stateProp.state.nodes()))   


    #def toEqnToTTFile(self, fileName, state):
    #    raise Exception("Not implemented")


    def getOutLogic(self, state):
        """Returns a string that describes the flop outputs given possible 
        input constraints vector==state"""

        flops = self.__flops
        logic = []
        for flop in flops:
            logic.append(self.__logic[flop])
            #logic.append(self.__stateProp.logic[flop])
        
        if state >= 2**len(flops):
            raise Exception("Invalid state " + str(state))

        stateStr = bin(state)[2:].rjust(len(flops), '0')

        output = applyInv(stateStr, logic)
        output = applyAnd(output)
        return output


    def getInLogic(self):
        outputs = []
        states = self.state()
        for state in states.states:
            stateStr = states.getStateStr(state)
            output = applyInv(stateStr, states.nodes())
            output = applyAnd(output)
            outputs.append(output)
        return applyOr(outputs)


        

