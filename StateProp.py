import DAGCircuit
import SimLib
import string
import State
import copy
import re
import Simulate
import myutils
from pygraph.classes.digraph import digraph
import subprocess

import pdb

class StateProp:
    "Processes a Gate-level netlist, propagating states through flops"
    def __init__(self, nl, reset=None, protocols=[], debug=0):

        self.__debug = debug

        self.__nl  = nl

        # create DAG from netlist
        self.__dag = DAGCircuit.DAGCircuit()

        print "Building DAG from netlist"
        self.__dag.fromNetlist(nl, remove=['clk', 'Clk', 'CLK'])

        for protocol in protocols:
            # add virtual gates to library
            nl.yaml.update(protocol.library())

            # connect virtual gates to DAG
            self.__dag.addInputProtocol(protocol)


        self.__lib = SimLib.SimLib(nl.yaml)    


        print "Breaking Flop Boundaries"
        self.__dag.breakFlops()

        # find primary-input dependencies of all nodes
        #(self.__deps, self.__deltas) = self.__findDeps__()
        print "Finding Node Dependencies"
        self.__calcDeps__()


        if self.__debug > 1:
            print self.__dag


        # initialize all states to nodes themselves
        # (this is needed for primary inputs as well as feedback paths)
        self.__logic = dict()
        self.__sim   = dict()
        self.__gen   = dict()
        for node in self.__dag.nodes():
            #self.__logic[node] = node
            self.__sim[node]   = node
            self.__gen[node]   = [node]

        print "Finding Reset State"

        # state object
        st = State.State([])
        if reset:
            flopsIn = self.__dag.flopsIn.keys()
            flopsIn.sort()
            flopsIn.reverse()
            flopsOut = map(self.__dag.flopsIn.get, flopsIn)
            st = State.State(flopsIn)

            if reset not in self.__dag.inputs:
                raise Exception("reset input `" + reset + "' is not in design!")

            sim = Simulate.Simulate(self, flopsOut)
            sim.setInputs({reset:True})
            state = []
            for flop in flopsOut:
                state.append(sim.simulate(flop))

            state = myutils.bool2int(state)

            #self.__state = tmp

            # propagate simulation equations in->out!
            #self.propSims()

            #pdb.set_trace()
            #tt = TruthTable.TruthTable(self, flopsOut)
            #self.__dag.flopsIn.values())

            #states = tt.sweepStates()
            #if len(states) > 1:
            #    raise Exception("More than 1 reset state found")

            #state = states.pop()

            if self.__debug > 0:
                print str("Found reset state for flops: " + 
                          str(flopsOut) + " " +
                          bin(state)[2:].rjust(len(st.nodes()), '0'))

            self.__reset = state
            st.addState(int(state))
        else:
            print "Warning: no reset signal given, assuming reset = 0"
            st.addState(int(0))

        self.__state = st

        #pdb.set_trace()

        # propagate node info
        #self.propEquations()
        #self.propSims()
        #self.propGenerators()


    def flopReport(self, maxSetSize=None):
        flopSet = self.flopSets()

        #try breaking large sets into smaller ones
        # this is conservative!!
        if maxSetSize:
            print "Note: Arbitrarily breaking large flopsets to be no larger than " + str(maxSetSize)
            # find sets that should be broken
            largeSets = set()
            for s in flopSet:
                if len(s) > maxSetSize:
                    largeSets.add(s)
            for s in largeSets:
                flopSet.remove(s)
                for newSet in myutils.chunker(s, maxSetSize):
                    flopSet.add(newSet)
                

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

            gr.add_node_attribute(state, {'inputs': inputs})

            # check if any of these inputs corresponds to an output from a
            # different state 
            for node in inputs:
                if node in self.__dag.flopsIn:
                    flop = self.__dag.flopsIn[node]
                    if flop in flopSetLookup:
                        edge = (flopSetLookup[flop], state)
                        if not gr.has_edge(edge):
                            gr.add_edge(edge)

        #print "The dependency graph for states is"
        #print gr
        return (gr, list(flopSet))


    def flopSets(self):
        return self.__findFlopSets__(self.__dag.flops)

    def __findFlopSets__(self, flopsIn):
        flops = copy.copy(flopsIn)
        flopGroup = set()

        # first lets try to group flops by name
        # WARNING: this is currently NOT very general!
        # start of hack attempt
        #constr_flops = []
        #for flop in flops:
        #    m = re.match("constr", flop)
        #    if m:
        #        constr_flops.append(flop)
        #for flop in constr_flops:
        #    flops.remove(flop)
        #if len(constr_flops) > 0:
        #    flopGroup.add(tuple(constr_flops))
        # end of hack attempt
        

        while len(flops) > 0:
            flop = flops.pop()
            m = re.match("(\S+_)(\d+)__(\d+)_$", flop)
            flopRoot = False
            #if m:
            #    flopRoot = m.group(1)
            #else:
            #    m = re.match("(\S+_)(\d+)_$", flop)
            #    if m:
            #        flopRoot = m.group(1)

            m = re.match("(\S+_)(\d+)_$", flop)
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
            else:
                print "Warning: Ignoring " + flop + " because it's not a bus"
                newflops = [flop]
                
            flopGroup.add(tuple(newflops))

                
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


    def propEquations(self):
        "build logic equations in->out"
        self.__propGeneric__(self.__logic, self.__lib.logic)

    def propSims(self):
        "simulate in->out"
        self.__propGeneric__(self.__sim, self.__lib.python)

    def propGenerators(self):
        "build generators in->out"
        self.__propGeneric__(self.__gen, self.__lib.gen)
    
    def __propGeneric__(self, results, libfuncs, garbage=False):
        "a generic function for build logic equations/simulating in->out"
        nl = self.__nl
        lib = self.__lib

        for node in self.__dag.order():
            if self.__dag.isInput(node):
                results[node] = [node]
            elif self.__dag.isCell(node):
                # go through all predecessors, construct dict of inputs
                inps = dict()
                for prev in self.__dag.node_incidence[node]:
                    for pin in self.__dag.pins((prev,node))[1]:
                        inps[pin] = results[prev]
                name = self.__dag.node2module(node)
                if len(inps) != len(lib.inputs[name]):
                    raise Exception("Not enough inputs on " + node)

                # construct arguments in order
                argList = []
                for arg in lib.inputs[name]:
                    argList.append(inps[arg])
                results[node] = libfuncs[name](*argList)

                if garbage:
                    for prev in self.__dag.node_incidence[node]:
                        # check if all successors have been processed
                        done = True
                        for succ in self.__dag.node_neighbors[prev]:
                            if not succ in results:
                                done = False
                                break
                        if done:
                            print "Garbage collecting " + prev
                            results.pop(prev)

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

        #self.propGenerators()
        #self.propSims()
        #self.propEquations()


    def defaultFlops(self):
        flops = list(self.__dag.flops)
        flops.sort()
        flops.reverse()
        return flops


    deps  = property(lambda self: self.__deps)
    stages= property(lambda self: self.__stages)
    orders= property(lambda self: self.__orders)
    lib   = property(lambda self: self.__lib)
    logic = property(lambda self: self.__logic)
    nl    = property(lambda self: self.__nl)
    sim   = property(lambda self: self.__sim)
    gen   = property(lambda self: self.__gen)
    dag   = property(lambda self: self.__dag)
    state = property(lambda self: self.__state)
    reset = property(lambda self: self.__reset)
