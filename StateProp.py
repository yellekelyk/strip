import DAGCircuit
from odict import OrderedDict
import utils
import SimLib
import string
import State
import copy
import re
import TruthTable


import pdb

class StateProp:
    "Processes a Gate-level netlist, propagating states through flops"
    def __init__(self, nl, init=None, fixFlopInput=True):

        self.__nl  = nl
        self.__lib = SimLib.SimLib(nl.yaml)

        # create DAG from netlist
        self.__dag = DAGCircuit.DAGCircuit()
        self.__dag.fromNetlist(nl, remove=['clk'])
        self.__dag.breakFlops()

        #label all nodes with a clock stage number (set self.__stages)
        (self.__stages, self.__flops) = self.__findStages__()


        # find primary-input dependencies of all nodes
        #(self.__deps, self.__deltas) = self.__findDeps__()
        self.__calcDeps__()


        # initialize all states to nodes themselves
        # (this is needed for primary inputs as well as feedback paths)
        self.__logic = dict()
        self.__sim   = dict()
        for node in self.__dag.nodes():
            self.__logic[node] = node
            self.__sim[node]   = node

        # state object
        st = State.State([])
        if fixFlopInput:
            st = State.State(self.__dag.flopsIn.keys())
        st.addState(int(0))
        self.__state = st


    def __findStages__(self):

        stages = dict()
        flops  = dict()
        for node in self.__dag.nodes():
            stages[node] = 0

        #nodes = self.__dag.bfs()
        nodes = self.__dag.order()

        for node in nodes:
            if len(self.__dag.node_incidence[node]) > 0:
                # find max of prev nodes
                prevMax = 0
                for prev in self.__dag.node_incidence[node]:
                    if stages[prev] > prevMax:
                        prevMax = stages[prev]
                stages[node] = prevMax

            # increment if node is flop
            if self.__dag.isCell(node):
                mod = self.__nl.mods[self.__nl.topMod].cells[node].submodname
                if "clocks" in self.__nl.yaml[mod]:
                    stages[node] = stages[node] + 1
                    flops[node] = stages[node]

            #print("setting stage for " + node + " to " + str(stages[node]))
        return (stages, flops)


    def __calcDeps__(self, root='__INPUTS__'):
        deps = dict()
        deltas = dict()

        # initialize all node attributes
        for node in self.__dag.nodes():
            deps[node]  = set()
            deltas[node] = 0
            

        # propagate dependencies
        ports = self.__nl.mods[self.__nl.topMod].ports
        for node in self.__dag.order(root):
            if self.__dag.isInput(node):
                deps[node].add(node)
                deltas[node] = 1
            else:
                # build up arguments from predecessors
                maxin = 0
                for prev in self.__dag.node_incidence[node]:
                    if len(deps[prev]) > maxin:
                        maxin = len(deps[prev])
                    for dep in deps[prev]:
                        deps[node].add(dep)

                deltas[node] = len(deps[node]) - maxin
        self.__deps = deps
        self.__deltas = deltas
                        

    def annotateState(self, state):
        "Annotate a group of inputs with a set of defined states"
        # do some checking of the inputs to make sure legal
        for node in state.nodes():
            if node not in self.__dag.inputs:
                raise Exception("Node " + node + " is not an input!")
            if node in self.__state.nodes():
                raise Exception("Node " + node + " cannot be added to multiple states")

        # aggregate into larger state of cross-products
        # len(self.__states) * len(newState)
        nodes = self.__state.nodes()
        nodes.extend(state.nodes())
        stateObj = State.State(nodes)
        if len(self.__state.states) > 0:
            for oldState in self.__state.states:
                for newState in state.states:
                    stateObj.addState(oldState * 2**(len(state.states)) + newState)
        else:
            stateObj = state
        
        self.__state = stateObj


    def propStates(self, fileName, flops=[]):
        "set all input states, run prop logic"
        for state in self.__state.states:
            for node in self.__state.nodes():
                val = self.__state.getState(state, node)
                self.__logic[node] = int(val)
                self.__sim[node]   = val

            self.propEquations()

            self.toEquationFile(str(fileName + "." + str(state)), flops)


    def propEquations(self):
        "build logic equations in->out"
        self.__propGeneric__(self.__logic, self.__lib.logic)

    def propSims(self):
        "simulate in->out"
        self.__propGeneric__(self.__sim, self.__lib.python)
    
    def __propGeneric__(self, results, libfuncs):
        "a generic function for build logic equations/simulating in->out"
        nl = self.__nl
        lib = self.__lib

        for node in self.__dag.order():
            if self.__dag.isCell(node):
                # go through all predecessors, construct dict of inputs
                inps = dict()
                for prev in self.__dag.node_incidence[node]:
                    for pin in self.__dag.pins((prev,node))[1]:
                        inps[pin] = str(results[prev])
                name = nl.mods[nl.topMod].cells[node].submodname
                if len(inps) != len(lib.inputs[name]):
                    raise Exception("Not enough inputs on " + node)

                # construct arguments in order
                argList = []
                for arg in lib.inputs[name]:
                    argList.append(inps[arg])
                results[node] = libfuncs[name](*argList)


    def pruneNodes(self, flops, maxIn = 15):
        for flop in flops:
            if len(self.__deps[flop]) > maxIn:
                print "Input set for " + flop + " is too large"
                deltas = dict()
                for node in self.__dag.reverseBFS(flop):
                    deltas[node] = self.__deltas[node]
                remove = max(deltas, key=deltas.get)
                print "Removing node " + remove
                # add new (fake) input in place of node
                portIn = remove + ".__dummy"
                self.__dag.addPortIn(portIn)
                # initialize entries for new node
                self.__logic[portIn] = portIn
                self.__sim[portIn]   = portIn

                # connect all children
                for child in self.__dag.node_neighbors[remove]:
                    if self.__dag.isCell(child):
                        edge = (remove, child)
                        wire = self.__dag.edge_label(edge)
                        pins = self.__dag.pins(edge)
                        for pin in pins[1]:
                            self.__dag.connect(portIn, child, wire, pins[0], pin)

                # remove the original node
                self.__dag.del_node(remove)

                # clean graph to remove dangling nodes
                self.__dag.clean()

                # recalculate deltas, deps
                self.__calcDeps__()



    def toEquationFile(self, fileName, flops = []):
        f = open(fileName, 'w')
        inputs = set()
        if len(flops) == 0:
            #flops = utils.invert(self.__flops)[1]
            flops = self.__flops.keys()
            flops.sort()
            flops.reverse()
        for flop in flops:
            inputs = set.union(inputs, self.__deps[flop])

        # remove any state-annotated inputs
        inputs = list(set.difference(inputs, self.__state.nodes()))
        
        # sort inputs for niceness
        inputs.sort()
        inputs.reverse()

        f.write("NAME = " + "TEST" + ";\n")
        f.write("INORDER = "  + string.join(inputs) + ";\n")
        f.write("OUTORDER = " + string.join(flops)  + ";\n")

        for flop in flops:
            f.write(flop + " = " + self.__logic[flop] + ";\n")

        f.close()


    def buildTT(self, flops = []):
        if len(flops) == 0:
            flops = self.__flops.keys()
            flops.sort()
            flops.reverse()

        # create anonymous functions for simulating
        outputs = []
        for flop in flops:
            inps = list(self.__deps[flop])
            #inps = list(self.__deps[flop].difference(self.__state.nodes()))

            ## ** MUST make clean lambda function input names!!!!
            evalStr = "lambda "
            for i in range(0, len(inps)-1):
                evalStr += inps[i] + ","
            evalStr += inps[len(inps)-1] + ": " + self.__sim[flop]
            # before evaluating, do regex replacing of input names
            for i in range(0, len(inps)):
                inp = re.sub("\[", "\\[", inps[i])
                inp = re.sub("\]", "\\]", inp)
                inp = re.sub("\.", "\\.", inp)
                evalStr = re.sub(inp, str("in"+str(i)), evalStr)
            func = eval(evalStr)
            outputs.append((inps, func))

        # create TT object
        return TruthTable.TruthTable(outputs)        

    def toTTFile(self, fileName, flops = [], debug=False):
        tt = self.buildTT(flops)

        # to work with fixed states, need to look at propStates() func above
        # and implement similar behavior for TT generation
        f = open(fileName, 'w')
        f.write(tt.tblHeader())
        if len(self.__state.states) > 0:
            for state in self.__state.states:
                for node in self.__state.nodes():
                    val = self.__state.getState(state, node)
                    tt.setInput(node, val)
                for line in tt.tblBody():
                    f.write(line)
                    if debug:
                        print line
        else:
            for line in tt.tblBody():
                f.write(line)
                if debug:
                    print line
        f.write(tt.tblFooter())
        f.close()


    def getStateSet(self, flops = []):
        tt = self.buildTT(flops)
        states = set()
        if len(self.__state.states) > 0:
            for state in self.__state.states:
                for node in self.__state.nodes():
                    val = self.__state.getState(state, node)
                    tt.setInput(node, val)
                for combo,outputs in tt.eval():
                    num = int(reduce(lambda x,y:str(str(x)+str(y)), 
                                     map(int,outputs)),2)
                    states.add(num)

        else:
            for combo,outputs in tt.eval(): 
                num = int(reduce(lambda x,y:str(str(x)+str(y)), 
                                map(int,outputs)),2)
                states.add(num)       

        return states

    flops = property(lambda self: self.__flops)
    deps  = property(lambda self: self.__deps)
    stages= property(lambda self: self.__stages)
    orders= property(lambda self: self.__orders)
    logic = property(lambda self: self.__logic)


