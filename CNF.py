import logic
import re
import pdb
import State
from odict import OrderedDict

class CNF:
    "Produces CNF format from Expr"
    def __init__(self, expr, inputs, states=State.State([]), verbose=0):

        self.__verbose = verbose

        # convert any bad characters in expr here
        expr = self.cleanStr(expr)

        exprOrig = expr
        allExprs = []

        for state in states.states:
            # reset to original
            expr = exprOrig

            # substitute constants into expression
            for node in states.nodes():
                val = states.getState(state, node)
                valStr = "0"
                if val:
                    valStr = "1"
                expr = re.sub(self.cleanStr(node), valStr, expr)

            allExprs.append(expr)
            
        if len(allExprs) == 0:
            allExprs = [exprOrig]

        exprStr = ""
        for i in range(0, len(allExprs)-1):
            exprStr += "(" + allExprs[i] + ") | " 
        exprStr += "(" + allExprs[len(allExprs)-1] + ")"

        print "Created expression: " + exprStr

        # create input map
        self.__inputs = OrderedDict()
        cnt=1
        for inp in inputs:
            inp = self.cleanStr(inp)
            self.__inputs[inp] = cnt
            cnt += 1

        #self.__expr = logic.to_cnf(exprStr)
        self.__expr = self.partialEval(logic.to_cnf(exprStr))


    def partialEval(self, cnfExpr):
        if cnfExpr.op == "&":
            if self.__verbose > 0:
                print "partialEval called on " + str(cnfExpr)
            remove = []
            for arg in cnfExpr.args:
                result = self.partialEval(arg)
                if result == True:
                    print str(arg) + " evaluates to 1, removing"
                    remove.append(arg)
                elif result == False:
                    print str(arg) + " evaluates to 0 ==> not SAT!"
                    raise Exception("Unimplemented case")
            for arg in remove:
                cnfExpr.args.remove(arg)
            return cnfExpr
        elif cnfExpr.op == "|":
            if self.__verbose > 0:
                print "partialEval called on " + str(cnfExpr)
            remove = []
            for arg in cnfExpr.args:
                result = self.partialEval(arg)
                if result == True:
                    return result
                elif result == False:
                    if self.__verbose > 0:
                        print str(arg) + " evaluates to 0, removing"
                    remove.append(arg)
            for arg in remove:
                cnfExpr.args.remove(arg)

            # check if ALL args have been removed
            if len(cnfExpr.args) == 0:
                return False
            return cnfExpr
        elif cnfExpr.op == "~":
            if self.__verbose > 0:
                print "partialEval called on " + str(cnfExpr)
            if cnfExpr.args[0] == logic.expr("1"):
                return 0
            elif cnfExpr.args[0] == logic.expr("0"):
                return 1
            else:
                return self.partialEval(cnfExpr.args[0])
        else:
            if self.__verbose > 0:
                print "partialEval called on " + str(cnfExpr)
            return cnfExpr.op


    def cleanStr(self, string):
        string = re.sub("!", "~", string)
        string = re.sub("\[", "_", string)
        string = re.sub("\]", "_", string)
        return string

    def toCNF(self):
        lines = 1
        args = [self.__expr]
        if self.__expr.op == "&":
            lines = len(self.__expr.args)
            args = self.__expr.args

        for inp in self.__inputs:
            yield "c " + str(self.__inputs[inp]) + ": " + inp

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
        #if str(expr) == "~reset":
            #pdb.set_trace()
            #print expr
            #print retStr
        return retStr
            
