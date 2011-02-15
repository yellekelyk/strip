import myutils
import re
import pdb

class Simulate:
    "Defines a class for simulating"
    def __init__(self, stateProp, flops=[]):
        self.__const = dict()
        self.__stateProp = stateProp

        self.__sim = dict()

        if len(flops) == 0:
            flops = stateProp.defaultFlops()

        self.__outputs = flops


    def setInputs(self, inputDict):
        for val in inputDict:
            self.__const[val] = inputDict[val]

        # clear intermediate results
        self.__sim = dict()

    def simulate(self, flop):
        if flop not in self.__outputs:
            raise Exception(flop + " not in output set")

        return self.__eval__(flop)


    def __eval__(self, node):

        if not node in self.__sim:
            dag = self.__stateProp.dag
            lib = self.__stateProp.lib
            nl = self.__stateProp.nl

            # base case: return name if it's a circuit input
            if dag.isInput(node):
                if node in self.__const:
                    return self.__const[node]
                else:
                    # we return a default value of 0 if not specified
                    return False

            else:
                inps = dict()
                for prev in dag.node_incidence[node]:
                    for pin in dag.pins((prev,node))[1]:
                        inps[pin] = self.__eval__(prev)
                name = nl.mods[nl.topMod].cells[node].submodname
                if len(inps) != len(lib.inputs[name]):
                    raise Exception("Not enough inputs on " + node)

                # construct arguments in order
                argList = []
                for arg in lib.inputs[name]:
                    argList.append(inps[arg])

                self.__sim[node] = lib.sim[name](*argList)

        return self.__sim[node]


