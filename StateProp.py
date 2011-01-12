import GateGraph
from odict import OrderedDict
import utils
import SimLib
import string

import pdb

class StateProp:
    "Processes a Gate-level netlist, propagating states through flops"
    def __init__(self, nl, init=None):

        #parse yaml file, create library of logic/simulation functions
        lib = SimLib.SimLib(nl.yaml)

        self.__nl = nl

        # create graph from netlist
        self.__gg = GateGraph.GateGraph(nl, remove=['clk'])

        #label all nodes with a clock stage number (set self.__stages)
        (self.__stages, self.__flops) = self.__findStages__()


        # find primary-input dependencies of all nodes
        self.__deps = self.__findDeps__()


        self.__orders = self.__findOrders__()


        # need to do:
        # identify potential output buses (outputs of all flops on same level)
        # enumerate states of those buses; logically reduce; repeat

        state = dict()
        # initialize all states to nodes themselves
        # (this is needed for primary inputs as well as feedback paths)
        for node in self.__gg.nodes():
            state[node] = node

        for i in range(0,1):
            for level in sorted(self.__orders.keys()):
                for node in self.__orders[level]:
                    if self.__gg.iscell(node):
                        # go through all predecessors, construct dict of inputs
                        inps = dict()
                        for prev in self.__gg.node_incidence[node]:
                            for pin in self.__gg.pins((prev,node))[1]:
                                inps[pin] = state[prev]
                        name = nl.mods[nl.topMod].cells[node].submodname
                        if len(inps) != len(lib.inputs[name]):
                            gg = self.__gg
                            pdb.set_trace()
                            raise Exception("Not enough inputs on " + node)

                        # construct arguments in order
                        argList = []
                        for arg in lib.inputs[name]:
                            argList.append(inps[arg])
                        state[node] = lib.logic[name](*argList)


        self.__state = state

    def __findStages__(self):

        stages = dict()
        flops  = dict()
        for node in self.__gg.nodes():
            stages[node] = 0

        for node in self.__gg.order():
            if len(self.__gg.node_incidence[node]) > 0:
                prevMin = 100000
                # find min of prev nodes
                for prev in self.__gg.node_incidence[node]:
                    if stages[prev] < prevMin:
                        prevMin = stages[prev]
                stages[node] = prevMin

            # increment if node is flop
            if self.__gg.iscell(node):
                mod = self.__nl.mods[self.__nl.topMod].cells[node].submodname
                if "clocks" in self.__nl.yaml[mod]:
                    stages[node] = stages[node] + 1
                    flops[node] = stages[node]

            #print("setting stage for " + node + " to " + str(stages[node]))
        return (stages, flops)


    def __findDeps__(self):
        deps = dict()

        # initialize all node attributes
        for node in self.__gg.nodes():
            deps[node]  = set()

        # propagate dependencies
        for node in self.__gg.order():
            if self.__gg.isport(node) and self.__nl.mods[self.__nl.topMod].ports[node].direction == "in":
                deps[node].add(node)
            else:
                # build up arguments from predecessors
                for prev in self.__gg.node_incidence[node]:
                    for dep in deps[prev]:
                        if dep not in deps[node]:
                            deps[node].add(dep)
        return deps

    def __findOrders__(self):

        orders = dict()

        #invert the stage dict
        stage_inv = utils.invert(self.__stages)

        # find and cache all levels of the circuit
        for level in stage_inv.keys():
            orders[level] = self.__gg.subgraph(stage_inv[level]).order(root=None)

        return orders
                        

#    def toLogicFile(self, fileName, level=1):
    def toLogicFile(self, fileName, flops = []):
        f = open(fileName, 'w')
        inputs = set()
        if len(flops) == 0:
            flops = utils.invert(self.__flops)[1]
        for flop in flops:
            inputs = set.union(inputs, self.__deps[flop])

        f.write("NAME = " + "TEST" + ";\n")
        f.write("INORDER = "  + string.join(inputs) + ";\n")
        f.write("OUTORDER = " + string.join(flops)  + ";\n")

        for flop in flops:
            f.write(flop + " = " + self.__state[flop] + ";\n")



    flops = property(lambda self: self.__flops)
    deps  = property(lambda self: self.__deps)
    stages= property(lambda self: self.__stages)
    orders= property(lambda self: self.__orders)
    state = property(lambda self: self.__state)
