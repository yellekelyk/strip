import re
from myutils import *

class SymbolicLogic:
    "A class for manpiulating Symbolic Boolean Logic"
    def __init__(self, stateProp, flops):
        if len(flops) == 0:
            flops = stateProp.defaultFlops()

        inputs = set()
        for flop in flops:
            inputs = set.union(inputs, stateProp.deps[flop])
        # remove any state-annotated inputs ? 
        inputs = list(inputs)
        inputs.sort()
        inputs.reverse()
        
        self.__flops  = flops
        self.__inputs = inputs
        #self.__stateProp = stateProp
        self.__logic  = stateProp.logic
        self.__state  = stateProp.state

    def inputs(self):
        return self.__inputs

    def outputs(self):
        return self.__flops

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
        #states = self.__stateProp.state
        states = self.__state
        for state in states.states:
            stateStr = states.getStateStr(state)
            output = applyInv(stateStr, states.nodes())
            output = applyAnd(output)
            outputs.append(output)
        return applyOr(outputs)


        

