import DAGCircuit
import SimLib
import string
import State
import copy
import re
import TruthTable
from pygraph.classes.digraph import digraph
import CNF
import subprocess

import pdb

class StateProp:
    "Processes a Gate-level netlist, propagating states through flops"
    def __init__(self, nl, reset=None):

        self.__nl  = nl
        self.__lib = SimLib.SimLib(nl.yaml)

        # create DAG from netlist
        self.__dag = DAGCircuit.DAGCircuit()
        self.__dag.fromNetlist(nl, remove=['clk'])
        self.__dag.breakFlops()

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
        if reset:
            flopsIn = self.__dag.flopsIn.keys()
            flopsIn.sort()
            flopsIn.reverse()
            flopsOut = map(self.__dag.flopsIn.get, flopsIn)
            st = State.State(flopsIn)

            inputs = list(self.__dag.inputs)
            if reset not in inputs:
                raise Exception("reset input `" + reset + "' is not in design!")
            inputs.remove(reset)
            inputs.append(reset)
            tmp = State.State(inputs)
            tmp.addState(int(1))
            self.__state = tmp

            # propagate simulation equations in->out!
            self.propSims()

            #pdb.set_trace()
            tt = TruthTable.TruthTable(self, flopsOut)
            #self.__dag.flopsIn.values())

            states = tt.sweepStates()
            if len(states) > 1:
                raise Exception("More than 1 reset state found")
            state = states.pop()

            print str("Found reset state for flops: " + 
                      str(flopsOut) + " " +
                      bin(state)[2:].rjust(len(st.nodes()), '0'))

            self.__reset = state
            st.addState(int(state))
        else:
            print "Warning: no reset signal given, assuming reset = 0"
            st.addState(int(0))

        self.__state = st

        # propagate node info
        self.propEquations()
        self.propSims()


    def flopReport(self):
        flopSet = self.flopSets()

        flopDict = dict()
        flopSetLookup = dict()

        # print out info about all state vectors 

        print "There were " + str(len(flopSet)) + " state vectors found"
        cnt = 0
        for flops in flopSet:
            flopDict[cnt] = flops
            print "Vector " + str(cnt) + ":"
            for flop in flops:
                # build inverse lookup for going from flop->flopSet
                flopSetLookup[flop] = cnt
                print flop
            cnt += 1


        # use graph package to keep track of any deps
        gr = digraph()
        for state in flopDict:
            gr.add_node(state)

        # determine dependencies among state vectors
        for state in flopDict:
            # find whole input set
            inputs = set()
            for node in flopDict[state]:
                inputs = set.union(inputs, self.__deps[node])

            gr.add_node_attribute(state, inputs)

            # check if any of these inputs corresponds to an output from a
            # different state 
            for node in inputs:
                if node in self.__dag.flopsIn:
                    flop = self.__dag.flopsIn[node]
                    edge = (flopSetLookup[flop], state)
                    if not gr.has_edge(edge):
                        gr.add_edge(edge)

        print "The dependency graph for states is"
        print gr
        return (gr, list(flopSet))


    def flopSets(self):
        return self.__findFlopSets__(self.__dag.flops)

    def __findFlopSets__(self, flopsIn):
        flops = copy.copy(flopsIn)
        flopGroup = set()
        while len(flops) > 0:
            flop = flops.pop()
            m = re.match("(\S+_)\d", flop)
            flopRoot = False
            if m:
                flopRoot = m.group(1)

            if flopRoot:
                newflops = []
                for f in flops:
                    if re.match(flopRoot, f):
                        newflops.append(f)

                for f in newflops:
                    flops.remove(f)
            
                newflops.append(flop)
                newflops.sort()
                newflops.reverse()
                flopGroup.add(tuple(newflops))
            else:
                print "Warning: Ignoring " + flop + " because it's not a bus"
                
        return flopGroup




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
                        
    def setInputState(self, state):
        # do some checking of the inputs to make sure legal
        for node in state.nodes():
            if node not in self.__dag.inputs:
                raise Exception("Node " + node + " is not an input!")
        self.__state = state

    def getInputState(self):
        return self.__state

    #def annotateState(self, state):
    #    "Annotate a group of inputs with a set of defined states"
    #    # do some checking of the inputs to make sure legal
    #    for node in state.nodes():
    #        if node not in self.__dag.inputs:
    #            raise Exception("Node " + node + " is not an input!")
    #        #if node in self.__state.nodes():
    #        #    raise Exception("Node " + node + " cannot be added to multiple states")
    #    self.__state = State.merge(self.__state, state)

        ## aggregate into larger state of cross-products
        ## len(self.__states) * len(newState)
        #nodes = self.__state.nodes()
        #nodes.extend(state.nodes())
        #stateObj = State.State(nodes)
        #for oldState in self.__state.states:
        #    for newState in state.states:
        #        stateObj.addState(oldState * 2**(len(state.states)) + newState)
        #
        #self.__state = stateObj


#    def propStates(self, fileName, flops=[]):
#        "set all input states, run prop logic"
#        for state in self.__state.states:
#            for node in self.__state.nodes():
#                val = self.__state.getState(state, node)
#                self.__logic[node] = int(val)
#                self.__sim[node]   = val
#
#            self.propEquations()
#
#            self.toEquationFile(str(fileName + "." + str(state)), flops)


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
                print "Input set for " + flop + " is " + str(len(self.__deps[flop]))
                deltas = dict()
                for node in self.__dag.reverseBFS(flop):
                    deltas[node] = self.__deltas[node]
                remove = max(deltas, key=deltas.get)
                print ("Removing node " + remove + " with " + 
                       str(deltas[remove]) + " inputs")
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


        self.propSims()
        self.propEquations()


    #def toEquationFile(self, fileName, flops = []):
    #    f = open(fileName, 'w')
    #    inputs = set()
    #    if len(flops) == 0:
    #        flops = list(self.__dag.flops)
    #        flops.sort()
    #        flops.reverse()
    #    for flop in flops:
    #        inputs = set.union(inputs, self.__deps[flop])
    #
    #    # remove any state-annotated inputs
    #    inputs = list(set.difference(inputs, self.__state.nodes()))
    #    
    #    # sort inputs for niceness
    #    inputs.sort()
    #    inputs.reverse()
    #
    #    f.write("NAME = " + "TEST" + ";\n")
    #    f.write("INORDER = "  + string.join(inputs) + ";\n")
    #    f.write("OUTORDER = " + string.join(flops)  + ";\n")
    #
    #    for flop in flops:
    #        f.write(flop + " = " + self.__logic[flop] + ";\n")
    #
    #    f.close()

    #def sweepSAT(self, flops):
    #    states = set()
    #    for i in range(0, 2**len(flops)):
    #        if self.runSAT(i, flops):
    #            states.add(i)
    #
    #    return states
    #
    #
    #def runSAT(self, state, flops):
    #
    #    fname = "/tmp/SAT."+str(state)+".logic"
    #    self.toLogicFile(fname, state, flops)
    #    l2cnf = "/home/kkelley/Downloads/logic2cnf-0.7.2/logic2cnf"
    #    sat   = "/home/kkelley/Downloads/minisat/core/minisat_static"
    #    p1 = subprocess.Popen([l2cnf, "-c", fname], stdout=subprocess.PIPE)
    #    p2 = subprocess.Popen([sat], 
    #                          stdin=p1.stdout, 
    #                          stdout=subprocess.PIPE,
    #                          stderr=subprocess.PIPE)
    #    out = string.split(p2.communicate()[0], "\n")
    #    result = out[len(out)-2]
    #    return result != "UNSATISFIABLE"
        
    #def toLogicFile(self, fileName, state, flops = []):
    #    f = open(fileName, 'w')
    #    inputs = set()
    #    if len(flops) == 0:
    #        flops = list(self.__dag.flops)
    #        flops.sort()
    #        flops.reverse()
    #    for flop in flops:
    #        inputs = set.union(inputs, self.__deps[flop])
    #
    #    # remove any state-annotated inputs
    #    inputs = list(inputs)
    #
    #    # sort inputs for niceness
    #    inputs.sort()
    #    inputs.reverse()
    #
    #    inputs = string.join(inputs)
    #    inputs = re.sub("\[", "_", inputs)
    #    inputs = re.sub("\]", "_", inputs)
    #    inputs = re.sub("\.", "_", inputs)
    #
    #    f.write("def "  + inputs + ";\n")
    #    output = self.__vecToLogic__(flops, state)
    #    
    #    states = self.__stateLogic__()
    #    if states:
    #        output = "(" + output + ")" + "&" + "(" + states + ")"
    #
    #    output = re.sub("\[", "_", output)
    #    output = re.sub("\]", "_", output)
    #    output = re.sub("\.", "_", output)
    #
    #    output = re.sub("&",  ".", output)
    #    output = re.sub("\|", "+", output)
    #    output = re.sub("!",  "~", output)
    #    
    #    f.write(output + ";\n")
    #    f.close()


    #def __vecToLogic__(self, flops, state):
    #    "Produces a logic equation that represents vector == state"
    #    
    #    if state >= 2**len(flops):
    #        raise Exception("Invalid state " + str(state))
    #
    #    stateStr = bin(state)[2:].rjust(len(flops), '0')
    #    output = ""
    #    for i in range(0, len(flops)-1):
    #        inv = ""
    #        if stateStr[i] == "0":
    #            inv = "!"
    #        output += "(" + inv + "(" + self.__logic[flops[i]] + "))& "
    #    inv = ""
    #    if stateStr[len(flops)-1] == "0":
    #        inv = "!"
    #    output += "(" + inv + "(" + self.__logic[flops[len(flops)-1]] + "))"
    #    return output

    #def __stateLogic__(self):
    #    states = []
    #    for state in self.__state.states:
    #        invLogic = []
    #        for node in self.__state.nodes():
    #            val = self.__state.getState(state, node)
    #            inv = ""
    #            if not val:
    #                inv = "!"
    #            invLogic.append(inv)
    #        stateStr = reduce(lambda x,y: str(x+"&"+y), 
    #                          map(lambda x,y: str("("+x+y+")"), 
    #                              invLogic, 
    #                              self.__state.nodes()))
    #        states.append("(" + stateStr + ")")
    #
    #    if len(states) > 0:
    #        states = reduce(lambda x,y: str(x+"|"+y), states)
    #    else:
    #        states = None
    #    return states

    #def toCNFFile(self, fileName, flops = [], verbose=0):
    #    f = open(fileName, 'w')
    #    inputs = set()
    #    if len(flops) == 0:
    #        flops = list(self.__dag.flops)
    #        flops.sort()
    #        flops.reverse()
    #    for flop in flops:
    #        inputs = set.union(inputs, self.__deps[flop])
    #
    #    # TODO remove any state-annotated inputs, deal with them!
    #    #inputs = list(inputs)
    #    inputs = list(set.difference(inputs, self.__state.nodes()))
    #    
    #    # sort inputs for niceness
    #    inputs.sort()
    #    inputs.reverse()
    #
    #    # build output logic
    #    # todo: put loop here to iterate over all possible outputs
    #    # for now it's at 'b1111
    #    #output = ""
    #    #for i in range(0, len(flops)-1):
    #    #    output += "(" + self.__logic[flops[i]] + ") & "
    #    #    if verbose > 0:
    #    #        print flops[i] + ": " + self.__logic[flops[i]]
    #    #output += "(" + self.__logic[flops[len(flops)-1]] + ")"
    #    output = self.__vecToLogic__(flops, 2**(len(flops))-1)
    #
    #    cnf = CNF.CNF(output, inputs, self.__state, verbose=verbose)
    #
    #    for line in cnf.toCNF():
    #        f.write(line + "\n")
    #
    #    f.close()

    def defaultFlops(self):
        flops = list(self.__dag.flops)
        flops.sort()
        flops.reverse()
        return flops


    #def buildTT(self, flops = []):
    #if len(flops) == 0:
    #    flops = list(self.__dag.flops)
    #    flops.sort()
    #    flops.reverse()
    #
    ## create anonymous functions for simulating
    #outputs = []
    #for flop in flops:
    #    inps = list(self.__deps[flop])
    #    #inps = list(self.__deps[flop].difference(self.__state.nodes()))
    #
    #    ## ** MUST make clean lambda function input names!!!!
    #    evalStr = "lambda "
    #    for i in range(0, len(inps)-1):
    #        evalStr += inps[i] + ","
    #    evalStr += inps[len(inps)-1] + ": " + self.__sim[flop]
    #    # before evaluating, do regex replacing of input names
    #    for i in range(0, len(inps)):
    #        inp = re.sub("\[", "\\[", inps[i])
    #        inp = re.sub("\]", "\\]", inp)
    #        inp = re.sub("\.", "\\.", inp)
    #        evalStr = re.sub(inp, str("in"+str(i)), evalStr)
    #    func = eval(evalStr)
    #    outputs.append((inps, func))

    # create TT object
    #return TruthTable.TruthTable(self, flops)        

    #def toTTFile(self, fileName, flops = [], debug=False):
    #    tt = self.buildTT(flops)
    #
    #    # to work with fixed states, need to look at propStates() func above
    #    # and implement similar behavior for TT generation
    #    f = open(fileName, 'w')
    #    f.write(tt.tblHeader())
    #    for state in self.__state.states:
    #        for node in self.__state.nodes():
    #            val = self.__state.getState(state, node)
    #            tt.setInput(node, val)
    #        for line in tt.tblBody():
    #            f.write(line)
    #            if debug:
    #                print line
    #
    #    f.write(tt.tblFooter())
    #    f.close()


    #def getStateSet(self, flops = []):
    #    tt = self.buildTT(flops)
    #    states = set()
    #    for state in self.__state.states:
    #        for node in self.__state.nodes():
    #            val = self.__state.getState(state, node)
    #            tt.setInput(node, val)
    #        for combo,outputs in tt.eval():
    #            num = int(reduce(lambda x,y:str(str(x)+str(y)), 
    #                             map(int,outputs)),2)
    #            states.add(num)
    #
    #    return states

    deps  = property(lambda self: self.__deps)
    stages= property(lambda self: self.__stages)
    orders= property(lambda self: self.__orders)
    logic = property(lambda self: self.__logic)
    sim   = property(lambda self: self.__sim)
    dag   = property(lambda self: self.__dag)
    state = property(lambda self: self.__state)
    reset = property(lambda self: self.__reset)
