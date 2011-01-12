import yaml
import re

class SimLib:
    "Holds simulation info for all primitive gates"
    def __init__(self, yaml):
        sim = dict()
        ins = dict()
        logic = dict()
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

                sim[modname] = eval(simStr)
                logic[modname] = eval(logicStr)
                ins[modname] = inputs
        self.__sim = sim
        self.__inputs = ins
        self.__logic = logic
    sim = property(lambda self: self.__sim)
    inputs = property(lambda self: self.__inputs)
    logic = property(lambda self: self.__logic)

    def __primToLogic__(self, inputs, prim):
        converts = [("and", "&"),
                    ("or", "|"),
                    ("not", "!"),
                    ("False", "ZERO"),
                    ("True", "ONE")]

        prim = "str(\"" + prim + "\")"

        for inp in inputs:
            #prim = re.sub(inp, str("\"(\" + str(" + inp + ") + \")\""), prim)
            prim = re.sub(inp, str("(\" + str(" + inp + ") + \")"), prim)


        for convert in converts:
            prim = re.sub(convert[0], convert[1], prim)

        return prim
