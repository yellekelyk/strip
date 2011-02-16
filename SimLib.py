import yaml
import re
import tokenize
import StringIO
import pdb

class SimLib:
    "Holds simulation info for all primitive gates"
    def __init__(self, yaml):
        sim = dict()
        ins = dict()
        logic = dict()
        python = dict()
        gen = dict()
        #aima = dict()

        eqntott = {"and": "&",
                   "or": "|",
                   "not": "!",
                   "False": "ZERO",
                   "True": "ONE"}

        #aimaC = {"and": "&",
        #         "or": "|",
        #         "not": "~",
        #         "False": "0",
        #         "True": "1"}

        for modname in yaml.keys():
            if "primitive" in yaml.get(modname):
                prim = yaml.get(modname)["primitive"]
                inputs = yaml.get(modname)["inputs"].keys()
                evalStr = "lambda "
                for i in range(0, len(inputs)-1):
                    evalStr += inputs[i] + ","
                evalStr += inputs[len(inputs)-1] + ": "
                simStr = evalStr + prim
                logicStr = evalStr + self.__primToLogic__(inputs, prim, eqntott)
                pyStr    = evalStr + self.__primToLogic__(inputs, prim)
                #aimaStr  = evalStr + self.__primToLogic__(inputs, prim, aimaC)

                genStr = self.__getGenerator__(yaml, modname, eqntott)
                
                d = {}
                exec genStr.strip() in d
                #setattr(self.__class__, modname, d[modname])
                gen[modname] = d[modname]
                sim[modname] = eval(simStr)
                logic[modname] = eval(logicStr)
                python[modname] = eval(pyStr)
                #aima[modname] = eval(aimaStr)
                ins[modname] = inputs
        self.__sim = sim
        self.__inputs = ins
        self.__logic = logic
        self.__python = python
        self.__gen = gen
        #self.__aima = aima
    sim    = property(lambda self: self.__sim)
    inputs = property(lambda self: self.__inputs)
    logic  = property(lambda self: self.__logic)
    python = property(lambda self: self.__python)
    gen    = property(lambda self: self.__gen)
    #aima   = property(lambda self: self.__aima)

    def __getGenerator__(self, yaml, modname, opMap):
        #ops = ["or", "and", "not"]

        prim = "(" + yaml.get(modname)["primitive"] + ")"
        inputs = yaml.get(modname)["inputs"].keys()
        execStr = "def " + modname + "("
        execStr += reduce(lambda x,y: x+ "," + y, inputs)
        execStr += "):\n"

        for token in tokenize.generate_tokens(StringIO.StringIO(prim).readline):
            # token is a NAME ... this can be not/and/or OR a variable name
            if token[0] == 1:
                if token[1] in opMap:
                    execStr += " yield \" " + opMap[token[1]] + " \"\n"
                elif token[1] in inputs:
                    execStr += " for stuff in " + token[1] + ":\n"
                    #execStr += "  yield \" \"\n"
                    execStr += "  yield stuff\n"
                    #execStr += "  yield \" \"\n"
                else:
                    raise Exception("Unknown token name: " + token[1])
            # token is an OP ... usually '(' or ')'
            elif token[0] == 51:
                execStr += " yield \"" + token[1] + "\"\n"
            # endmarker
            elif token[0] == 0:
                pass
            else:
                raise Exception("Unexpected token: " + str(token))

        return execStr


    def __primToLogic__(self, inputs, prim, converts=None):
        prim = "str(\"" + prim + "\")"

        for inp in inputs:
            prim = re.sub(inp, str("(\" + str(" + inp + ") + \")"), prim)

        if converts:
            for convert in converts:
                prim = re.sub(convert, converts[convert], prim)

        return prim
