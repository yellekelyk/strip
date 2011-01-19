import yaml
import re

class SimLib:
    "Holds simulation info for all primitive gates"
    def __init__(self, yaml):
        sim = dict()
        ins = dict()
        logic = dict()
        python = dict()
        for modname in yaml.keys():
            if "primitive" in yaml.get(modname):
                prim = yaml.get(modname)["primitive"]
                inputs = yaml.get(modname)["inputs"].keys()
                evalStr = "lambda "
                for i in range(0, len(inputs)-1):
                    evalStr += inputs[i] + ","
                evalStr += inputs[len(inputs)-1] + ": "
                simStr = evalStr + prim
                logicStr = evalStr + self.__primToLogic__(inputs, prim)
                pyStr    = evalStr + self.__primToLogic__(inputs, prim, True)

                sim[modname] = eval(simStr)
                logic[modname] = eval(logicStr)
                python[modname] = eval(pyStr)
                ins[modname] = inputs
        self.__sim = sim
        self.__inputs = ins
        self.__logic = logic
        self.__python = python
    sim = property(lambda self: self.__sim)
    inputs = property(lambda self: self.__inputs)
    logic  = property(lambda self: self.__logic)
    python = property(lambda self: self.__python)

    def __primToLogic__(self, inputs, prim, python=False):
        converts = [("and", "&"),
                    ("or", "|"),
                    ("not", "!"),
                    ("False", "ZERO"),
                    ("True", "ONE")]

        prim = "str(\"" + prim + "\")"

        for inp in inputs:
            #prim = re.sub(inp, str("\"(\" + str(" + inp + ") + \")\""), prim)
            prim = re.sub(inp, str("(\" + str(" + inp + ") + \")"), prim)

        if not python:
            for convert in converts:
                prim = re.sub(convert[0], convert[1], prim)

        return prim
