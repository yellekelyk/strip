import yaml
import re

class SimLib:
    "Holds simulation info for all primitive gates"
    def __init__(self, yaml):
        sim = dict()
        ins = dict()
        logic = dict()
        python = dict()
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

                sim[modname] = eval(simStr)
                logic[modname] = eval(logicStr)
                python[modname] = eval(pyStr)
                #aima[modname] = eval(aimaStr)
                ins[modname] = inputs
        self.__sim = sim
        self.__inputs = ins
        self.__logic = logic
        self.__python = python
        #self.__aima = aima
    sim    = property(lambda self: self.__sim)
    inputs = property(lambda self: self.__inputs)
    logic  = property(lambda self: self.__logic)
    python = property(lambda self: self.__python)
    #aima   = property(lambda self: self.__aima)

    def __primToLogic__(self, inputs, prim, converts=None):
        prim = "str(\"" + prim + "\")"

        for inp in inputs:
            prim = re.sub(inp, str("(\" + str(" + inp + ") + \")"), prim)

        if converts:
            for convert in converts:
                prim = re.sub(convert, converts[convert], prim)

        return prim
