from SymbolicLogic import *
import logic
import re
import pdb
import State
from odict import OrderedDict

class CNF(SymbolicLogic):
    "Produces CNF format from Expr"
    def __init__(self, stateProp, flops=[], verbose=0):
        SymbolicLogic.__init__(self, stateProp, flops)
        self.__verbose = verbose
        inputs = map(self.cleanNames, self.inputs())
        self.__inputs = OrderedDict(zip(inputs, range(1,len(inputs)+1)))


    def fileHeader(self):
        output = ''
        for inp in self.__inputs:
            output += "c " + str(self.__inputs[inp]) + ": " + inp + "\n"
        return output
    

    def fileBody(self, state):
        exprStr = applyAnd([self.getOutLogic(state), self.getInLogic()])
        exprStr = self.cleanNames(exprStr)
        exprStr = self.convertOps(exprStr)
        expr = logic.to_cnf(exprStr, self.__verbose)
        output = ''
        for line in self.toCNF(expr):
            output += line + "\n"
        return output

    def cnf(self, state):
        return self.fileBody(state)

    def cleanNames(self, string):
        string = re.sub("\[", "_", string)
        string = re.sub("\]", "_", string)
        return string

    def convertOps(self, string):
        string = re.sub("!", "~", string)
        return string


    def toCNF(self, expr):
        lines = 1
        args = [expr]
        if expr.op == "&":
            lines = len(expr.args)
            args = expr.args

        yield "p cnf " + str(len(self.__inputs)) + " " + str(lines)

        for arg in args:
            yield self.__toCNF__(arg)

    def __toCNF__(self, expr):
        args = [expr]
        if expr.op == "&":
            raise Exception("Not CNF: " + expr)
        elif expr.op == "|":
            args = expr.args

        retStr = ""
        for arg in args:
            if arg.op == "~":
                retStr += "-" + str(self.__inputs[str(arg.args[0])]) + " "
            elif arg.op == "&":
                raise Exception("Not CNF: " + str(arg))
            else:
                retStr += str(self.__inputs[arg.op]) + " "
                if len(arg.args) > 0:
                    raise Exception("Strange arg " + arg)
        retStr += "0"
        return retStr
        
    
    # **** KEEP this function -- it seemed to work, might want in future ***
    #def partialEval(self, cnfExpr):
    #    raise Exception("This is an experimental feature")
    #    if cnfExpr.op == "&":
    #        if self.__verbose > 0:
    #            print "partialEval called on " + str(cnfExpr)
    #        remove = []
    #        for arg in cnfExpr.args:
    #            result = self.partialEval(arg)
    #            if result == True:
    #                print str(arg) + " evaluates to 1, removing"
    #                remove.append(arg)
    #            elif result == False:
    #                print str(arg) + " evaluates to 0 ==> not SAT!"
    #                raise Exception("Unimplemented case")
    #        for arg in remove:
    #            cnfExpr.args.remove(arg)
    #        return cnfExpr
    #    elif cnfExpr.op == "|":
    #        if self.__verbose > 0:
    #            print "partialEval called on " + str(cnfExpr)
    #        remove = []
    #        for arg in cnfExpr.args:
    #            result = self.partialEval(arg)
    #            if result == True:
    #                return result
    #            elif result == False:
    #                if self.__verbose > 0:
    #                    print str(arg) + " evaluates to 0, removing"
    #                remove.append(arg)
    #        for arg in remove:
    #            cnfExpr.args.remove(arg)
    #
    #        # check if ALL args have been removed
    #        if len(cnfExpr.args) == 0:
    #            return False
    #        return cnfExpr
    #    elif cnfExpr.op == "~":
    #        if self.__verbose > 0:
    #            print "partialEval called on " + str(cnfExpr)
    #        if cnfExpr.args[0] == logic.expr("1"):
    #            return 0
    #        elif cnfExpr.args[0] == logic.expr("0"):
    #            return 1
    #        else:
    #            return self.partialEval(cnfExpr.args[0])
    #    else:
    #        if self.__verbose > 0:
    #            print "partialEval called on " + str(cnfExpr)
    #        return cnfExpr.op
