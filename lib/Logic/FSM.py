import ast
from lib.Utils import codegen
import copy
import math
import pdb

class FSM:
    class ReadLogic(ast.NodeVisitor):
        "Parses a logical expression to find the unique inputs"
        def __init__(self, logic):
            self.__inputs = set()
            ast.NodeVisitor.visit(self, ast.parse(logic))

        def generic_visit(self, node):
            ast.NodeVisitor.generic_visit(self, node)

        def visit_Name(self, node):
            self.__inputs.add(node.id)
            ast.NodeVisitor.generic_visit(self, node)
        
        def inputs(self):
            return self.__inputs

    class ChangeLogic(ast.NodeTransformer):
        def __init__(self, logic, transform):
            self.__ast = ast.parse(logic)
            self.__transform = transform
            ast.NodeTransformer.visit(self, self.__ast)

        def visit_Name(self, node):
            if node.id in self.__transform:
                node.id = self.__transform[node.id]
            return node

        def code(self):
            return codegen.to_source(self.__ast)


    """Parses one FSM structure, creates virtual logic that describes it"""
    def __init__(self, name, desc):
        # verify that the FSM description is complete
        for key in ["inputs", "outputs", "nextstate", "reset"]:
            if not key in desc:
                raise Exception("Missing " + key + " in FSM " + fsm)

        # make sure reset state exists!
        if not desc["reset"] in desc["nextstate"].keys():
            raise Exception("Reset state " + desc["reset"] + 
                            " not in state list")
        
        
        # save description
        self.__name = name
        self.__desc = desc
        
        self.__library = dict()

        # create state map (maps abstract state to bit-representation)
        # loop over each state expression
        self.__stateMap = dict()
        nBits = self.nBits(len(desc["nextstate"].keys()))
        for stNum in range(len(desc["nextstate"].keys())):
            bitVals  = map(lambda x: bool(int(x)), 
                           list(bin(stNum)[2:].rjust(nBits, '0')))
            bitNames = range(nBits)
            bitNames.reverse()
            bitNames = map(lambda x: self.__name+"_state_"+str(x), bitNames)
            expr = map(lambda x,y: "("+x+")" if y else "(not "+x+")", 
                       bitNames, bitVals)
            expr = reduce(lambda x,y: x + " and " + y, expr)
            self.__stateMap[desc["nextstate"].keys()[stNum]] = expr

        # create the gates!
        # bits   = int(math.ceil(math.log(len(states),2)))
        # will need "2*bits + outputs" gates (bits for ns gates, bits flops)
        self.__createStateGates__()
        self.__createNextStateGates__()
        self.__createOutputGates__()


    def __createStateGates__(self):
        """All state gates will be simple flops"""
        self.__states = dict()

        self.__library["VirtualFF"] = {
            "clocks" : {"CP" : 1},
            "inputs" : {"D"  : 1},
            "outputs": {"Q"  : 1},
            "primitive": "D"
            }
        
        nBits = self.nBits(len(self.__desc["nextstate"].keys()))
        for bit in range(nBits):
            self.__states[self.__name+"_state_"+str(bit)] = "VirtualFF"
        #for st in self.__desc["nextstate"].keys():
        #    self.__states[self.__stateMap[st]] = "VirtualFF"


    def __toBits__(self, name, reset=True):
        # (use copy to preserve original)
        tmp = copy.deepcopy(self.__desc[name])
        for st in tmp.keys():

            # add reset logic (needed for nextstates)
            if reset:
                if st == self.__desc["reset"]:
                    tmp[st] = "(" + tmp[st] + ") or reset"
                else:
                    tmp[st] = "(" + tmp[st] + ") and (not reset)"
                
            # convert abstract states to bits
            tmp[st] = FSM.ChangeLogic(tmp[st], self.__stateMap).code()

        return tmp


    def __createNextStateGates__(self):
        """Each state bit will have custom next state logic"""

        # build one gate for each state bit
        ns = self.__toBits__("nextstate")
        nBits = self.nBits(len(ns.keys()))
        exprs = dict()
        for bit in range(nBits):
            tmp = []
            # loop over each state expression
            for stNum in range(len(ns.keys())):
                # check if this bit appears in stNum
                if bin(stNum)[2:].rjust(nBits, '0')[nBits-bit-1] == '1':
                    tmp.append("("+ns[ns.keys()[stNum]]+")")

            name = self.__name + "_state_" + str(bit)

            # now expr is the full expression for this bit
            #exprs.append(reduce(lambda x,y: x + " or " + y, tmp))
            exprs[name] = reduce(lambda x,y: x + " or " + y, tmp)

        self.__nextstates = self.__createGenericGates__(exprs, "nextstate_")



    def __createOutputGates__(self):
        """Each output bit has its own custom gate"""

        # build one gate for each output
        exprs = self.__toBits__("outputs", False)

        self.__outputs = self.__createGenericGates__(exprs)



    def __createGenericGates__(self, exprs, prefix=None):
        
        results = dict()

        for name in exprs.keys():
            #gateName = name + "_" + str(bit)
            #expr = exprs[bit]
            gateName = prefix + name if prefix else name

            if gateName in self.__library:
                raise Exception("Something's gone wrong!")

            self.__library[gateName] = {
                "outputs": {"out" : 1},
                "primitive": exprs[name]
                }

            inps = FSM.ReadLogic(exprs[name]).inputs()
            self.__library[gateName]["inputs"] = dict(zip(inps, [1]*len(inps)))
            results[name] = gateName

        return results



    def nBits(self, nstates):
        return int(math.ceil(math.log(nstates,2)))

    def states(self):
        """ Returns states dict (state name --> name of gate in library)"""
        return self.__states

    def outputs(self):
        """ Returns outputs dict (output name --> name of gate in library"""
        return self.__outputs

    def nextStates(self):
        """ Returns nextstates dict (state name --> name of gate in library"""
        return self.__nextstates


    def library(self):
        """ Return a hash structure of our custom library """
        return self.__library

        
