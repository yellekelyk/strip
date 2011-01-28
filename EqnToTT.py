from SymbolicLogic import *

class EqnToTT(SymbolicLogic):
    def __init__(self, stateProp, flops=[], verbose=0):
        SymbolicLogic.__init__(self, stateProp, flops)
        self.__verbose = verbose

        # sort inputs for niceness
        inputs = list(set.difference(SymbolicLogic.inputs(self), 
                                     stateProp.states.nodes()))
        inputs.sort()
        inputs.reverse()
        self.__inputs = inputs

    def inputs(self):
        return self.__inputs

    def fileHeader(self):
        output =  "NAME = " + "TEST" + ";\n"
        output += "INORDER = "  + string.join(self.inputs())  + ";\n"
        output += "OUTORDER = " + string.join(self.outputs()) + ";\n"
        return output

    def fileBody(self, state):
        raise Exception("This hasn't been finished/verified")
        output = applyAnd([self.getOutLogic(state), self.getInLogic()])
        return output + ";\n"
