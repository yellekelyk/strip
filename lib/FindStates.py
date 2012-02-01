from Logic import DAG2CNF
from Logic import InputFSMs
from Logic import SATInc
from Logic import StateProp
from Logic import TruthTable

from Utils import myutils
from Verilog import Netlist

from Utils import State
from Utils import StateSuperset
from Utils import StateGroup

import copy
import glob
import os
from pygraph.algorithms.searching import depth_first_search
import re
import sys
import string
import time

import gc
import cProfile
import pdb


class FindStates:
    def __init__(self, options):

        self.__verbose = options['verbose']

        self.initTime = time.time()
        self.__dag2cnf = None

        design = options['design']
        nl = Netlist.Netlist()
        for infile in glob.glob(os.path.join(options['design_dir'], '*.yml')):
            print "Reading " + infile
            nl.readYAML(infile)
        print "Linking " + design
        nl.link(design)

        self.start = time.time()

        print "Building DAG"
        if 'reset' in nl.mods[design].ports:
            reset = 'reset'
        elif 'Reset' in nl.mods[design].ports:
            reset = 'Reset'
        else:
            raise Exception("Couldn't find reset signal")
        
        print "Design has " + str(len(nl.mods[design].cells)) + " gates"

        fsms = InputFSMs.InputFSMs(nl)
        for fileName in options['inputs']:
            fsms.readYAML(fileName)

        self.__MAX_SIZE=options['window_size']
        self.__OVERLAP=options['window_step']
        self.__MAX_STATES=2**options['max_states']


        self.__sp = StateProp.StateProp(nl, reset, fsms.protocols())


        if options['read_groups']:
            gFile = options['read_groups']
            print "Using user-specified groupings in: " + gFile
            (self.__gr, self.__flopGroups) = self.__sp.readGroups(gFile)
            supersets = set()
        else:
            print "Building groups according to programmed rules"
            (self.__gr, self.__flopGroups) = self.__sp.buildGroups()

            # todo consider phasing out private data member 
            # self.__flopGroups, since it becomes redundant once
            # we have created self.__flopStatesOut below
            # self.__flopGroups[grp] == self.__flopStatesOut.lookup(grp).nodes()

            # DIFFERENCE for protocol
            supersets = self.__combineGroupsByStr__(options['protocol_fifo'])
        
            #supersets = self.__combineGroupsByStr__("_capacity_")
            #supersets = self.__combineGroupsByStr__("_valid_")
            #supersets = self.__combineGroupsByStr__("_state_")
            #supersets = set()


        print "Finding Flops"
        if options['dump_groups']:
            dump = open(options['dump_groups'], 'w')

            #print "Found " + str(len(self.__gr.nodes())) + " groups"
            for grp in self.__gr.nodes():
                dump.write(str(grp) + ":" + '\n')
                for flop in self.__flopGroups[grp]:
                    dump.write('  ' + flop + '\n')
            dump.close()
            exit(0)



        if self.__verbose > 1:
            print self.__gr

        # set user-specified input constraints here!
        self.__userStates = StateGroup.StateGroup()
        # DIFFERENCE for protocol (commented out old code ... the new scheme
        # should handle this anyway
        #if len(sys.argv) > 2:
        #    self.__userStates.readYAML(sys.argv[2])
        #    # do a check on the node names specified in user constraints file
        #    for node in self.__userStates.nodes():
        #        if node in nl.mods[design].ports:
        #            if nl.mods[design].ports[node].direction != "in":
        #                raise Exception("User-specified node " + node + " is not an input port in design " + design)
        #        else:
        #            raise Exception("User-specified node " + node + " is not in module port list for design " + design)


        # set root node for reverse post-ordering
        nodes = self.__gr.nodes()
        self.__gr.add_node(-1)
        for node in nodes:
            for inp in self.__gr.node_attr[node][0]['inputs']:
                if inp in nl.mods[design].ports:
                    if nl.mods[design].ports[inp].direction == "in":
                        edge = (-1, node)
                        if not self.__gr.has_edge(edge):
                            self.__gr.add_edge(edge)
            
                

        # find iteration order (reverse postorder)
        st, pre, self.__post = depth_first_search(self.__gr, root=-1)
        self.__post.reverse()     
        self.__post.remove(-1)




        # initialization code
        # description of data members
        # flopStatesOut: maps group->(State for all outputs)
        # flopStatesIn: aggregated input state combinations for fixed inputs
        # flopStatesIn_p: previous version of flopStatesIn
        # inputs: maps group output -> constrained input
        # flopsIn: maps group -> constrained inputs
        self.__flopStatesOut = StateGroup.StateGroup()
        self.__flopStatesIn_p = dict()
        self.__inputs = dict() 
        self.__flopsIn = dict()
        outToIn = myutils.invert(self.__sp.dag.flopsIn, True)
        self.__outToIn = outToIn
        self.__cnt = dict()

        for group in self.__post:
            self.__inputs[group] = map(outToIn.get, self.__flopGroups[group])
            while None in self.__inputs[group]:
                self.__inputs[group].remove(None)
            reset_in  = State.subset(self.__sp.state, 
                                     self.__inputs[group])
            reset_out = State.rename(reset_in, 
                                     self.__sp.dag.flopsIn)
            if group in supersets:
                # if this is a combo group, we should update
                # the superset and then store it
                #pdb.set_trace()
                supersets[group].update(reset_out)
                self.__flopStatesOut.insert(group, supersets[group])
            else:
                # otherwise, store the regular State object
                self.__flopStatesOut.insert(group, reset_out)

            flopsIn = set.intersection(set(self.__gr.node_attr[group][0]['inputs']), 
                                       set(self.__sp.dag.flopsIn.keys()))
            self.__flopsIn[group] = flopsIn
            self.__cnt[group] = 0

        # create empty flopStatesIn_p for each group
        for group in self.__post:
            # these are ALL flop inputs for the current group
            flopsIn = self.__flopsIn[group]
            flopsOut = map(self.__sp.dag.flopsIn.get, flopsIn)
            inStates = self.__flopStatesOut.subset(flopsOut).rename(self.__outToIn)
            sg = StateGroup.StateGroup()
            sg.initGroups(inStates)
            self.__flopStatesIn_p[group] = sg


    def __combineGroupsByStr__(self, search):
        """Merge ALL fanin nodes that match search"""
        testGroups = []
        for grp in self.__gr.nodes():
            if re.search(search, self.__flopGroups[grp][0]):
                testGroups.append(grp)

        print "Found special groups: " + str(testGroups)

        # build a list of sets, each set are the groups being combined
        allGroups = []
        for grp in testGroups:
            combineGroups = set(self.__gr.node_incidence[grp])
            if grp in combineGroups:
                combineGroups.remove(grp)
            allGroups.append(combineGroups)

        return self.__combineGroups__(allGroups)



    def __combineGroups__(self, allGroups):
        # only add 1 node to graph
        newGroup = len(self.__gr.nodes())

        # add new group to graph, create proper edges
        self.__gr.add_node(newGroup)
        newGroupInputs = set()
        states = []
        for combine in allGroups:
            comboNodes = list()
            for grp in combine:
                for node in self.__gr.node_incidence[grp]:
                    edge = (newGroup,node)
                    if not self.__gr.has_edge(edge):
                        self.__gr.add_edge(edge)
                for node in self.__gr.node_neighbors[grp]:
                    edge = (node,newGroup)
                    if not self.__gr.has_edge(edge):
                        self.__gr.add_edge(edge)
                newGroupInputs = newGroupInputs.union(self.__gr.node_attr[grp][0]['inputs'])
                comboNodes.extend(self.__flopGroups[grp])

            states.append(State.State(comboNodes))
            print "Adding special state: " + str(comboNodes)

        for combine in allGroups:
            for grp in combine:
                if self.__gr.has_node(grp):
                    self.__gr.del_node(grp)

        ss = StateSuperset.StateSuperset(states)

        self.__gr.add_node_attribute(newGroup, 
                                     {'inputs': newGroupInputs,
                                      'combo': True})
        self.__flopGroups[newGroup] = tuple(ss.nodes())

        # return an empty state superset object
        return {newGroup: ss}


    def run(self):
        "Main loop"
        updated = True
        while updated:
            print "Start of main loop..."
            updated = self.runAllGroups()


    def runAllGroups(self):
        "Run one iteration of the algorithm over all groups"
        ret = False

        for group in self.__post:
            if not self.__flopStatesOut.get(group).full():
                #if not self.__skip[group]:
                start = time.time()

                (updated, inputs) = self.checkInputs(group)
                
                dur = time.time() - start
                print "checkInputs() took " + str(dur) + " seconds"
              
                if updated or self.__cnt[group] == 0:
                    # mark a global update
                    ret = True
                    # mark this group as being run again
                    self.__cnt[group] += 1

                    # updates the outputs for group
                    self.runGroup(group, inputs)

        return ret

    def checkInputs(self, group):
        "checks to see if group has any new input constraints"
        
        # these are ALL flop inputs for the current group
        flopsIn = self.__flopsIn[group]

        # lookup the previous input state for this group
        inStates_p = self.__flopStatesIn_p[group]

        # calculate the current input state for this group
        flopsOut = map(self.__sp.dag.flopsIn.get, flopsIn)

        inStates = self.__flopStatesOut.subset(flopsOut).rename(self.__outToIn)

        updated = True
        # determine if anything has been updated
        if set(inStates.nodes()) == set(inStates_p.nodes()):
            if inStates == inStates_p:
                updated = False
        else:
            inStates_p = StateGroup.StateGroup()
            inStates_p.initGroups(inStates)

        diffStates = inStates.diff(inStates_p)

        print str(str(group) + ": There were " + 
                  str(len(self.__flopStatesIn_p[group].nodes())-
                      len(inStates.nodes())) + 
                  " input constraints dropped")      

        # set previous state
        self.__flopStatesIn_p[group] = inStates

        return (updated, diffStates)


    def runGroup(self, group, inputs):
        "Run one pass for group, using inputs as state diff"

        statesOut = self.__flopStatesOut.get(group)
        if statesOut.full():
            raise Exception("Shouldn't call if skip is true!")

        inputSet  = self.__gr.node_attr[group][0]['inputs']
        constIn = list(set.intersection(inputSet, set(inputs.nodes())))
        # find number of inputs that we have to sweep
        inputCombos = 2**(len(inputSet)-len(constIn)) + inputs.numStates()

        # add user-specified input constraints before running
        userConstraints = self.__userStates.states()
        userKey = -1
        for st in userConstraints:
            inputs.insert(userKey,userConstraints[st])
            userKey -= 1
        self.__sp.setInputState(inputs)

        # todo remove this  ... it's only a test!!!
        # *********************************
        inputCombos = 2**16
        
        idx = 0
        for stateOut in statesOut.subgroups():
            outputSet = stateOut.nodes()

            # with superset groups some smaller groups may be full
            if stateOut.full():
                continue
                #pdb.set_trace()
                #raise Exception("Need to do something smarter here!")

            print "Considering outputs (" + str(len(outputSet)) + "): " + str(outputSet)        

            # find number of outputs that haven't been SATISFIED
            outputCombos = stateOut.numAllStates()-stateOut.numStates()

            # TODO: stop simulation/SAT sweep early if > half states seen
            # TODO: avoid TT simulation if logic cone is large 
            if inputCombos < 2**16:
                # do simulation to get output states
                print "Running simulation sweep..."
                tt = TruthTable.TruthTable(self.__sp, outputSet)
                states = tt.sweepStates()
            
            else:
                states = self.runSAT(stateOut)

                if states:
                    states = states.states

                else:
                    print "Skipping this group from now on!"
                    states = set()
                    stateOut.setSkip()

            #elif outputCombos < 2**self.__MAX_SIZE:
            #
            #    # do SAT
            #    print "Running SAT..."
            #
            #    outputStates = list(set.difference(set(range(2**len(outputSet))), stateOut.states))
            #    states = runSingleSAT(self.__sp, 
            #                          outputSet, 
            #                          st=outputStates).states
            #
            #
            #else:
            #    # FrEaK OuTTT!
            #    print (str("Skipping b/c input combos are " + str(inputCombos) +
            #               " and Output size is " + str(len(outputSet))))
            #    states = set()
            #    stateOut.setSkip()

            if len(states) < 2**9:
                print "reached " + str(len(states)) + " states: " + str(states)
            else:
                print "reached " + str(len(states)) + " states: (hidden for length)"

            for st in states:
                stateOut.addState(st)

            #if len(states) > 0:
            #    assumpFile = dag2cnf.assumpFileIn(group, idx)
            #    print "Removing existing assumption file " + assumpFile
            #    os.remove(assumpFile)

            idx += 1


    def runSAT(self, stateOut):
        """ Run SAT on all states; if there are too many states then 
        we attempt to prune some of the possibilties first and only run on the 
        remainder 

        stateOut is a State object; 
        we want to run on 2**len(stateOut.nodes())-stateOut.states() possibilities
        
        """
        
        newStates = []
        numNewStates = 0

        #maxFinal = 2**maxSize
        #maxFinal = 2**19
        #maxFinal = 2**21
        maxFinal = self.__MAX_STATES

        allStates = copy.deepcopy(stateOut)

        for newNodes in myutils.chunker_ol(stateOut.nodes(), 
                                           self.__MAX_SIZE, 
                                           self.__OVERLAP):

            start = time.time()

            newState, existingStates = State.subset_c(allStates, newNodes)

            dur = time.time() - start
            print "state separation took " + str(dur) + " seconds"


            statesToSweep = list(newState.not_states)
            if len(statesToSweep) > 0:
                newlyReached = self.runSingleSAT(newState.nodes(), st=statesToSweep)
            else:
                newlyReached = State.State(newState.nodes())
        
            nInterim = str(len(newlyReached.states))
            if len(newlyReached.states) < 2**9:
                print "reached " + nInterim + " (" + str(len(existingStates.states)) + ") interim states: " + str(newlyReached.states)
            else:
                print "reached " + nInterim + "(" + str(len(existingStates.states)) + ") interim states: (hidden for length)"

            numNewStates += len(existingStates.states) * len(newlyReached.states)

            if numNewStates > maxFinal:
                print "We just reached " + str(numNewStates) + " to test, I quit"
                return None

            start = time.time()
            for st in newlyReached.states:
                newState.addState(st)

            tmpStates = State.State(stateOut.nodes())
            if len(newlyReached.states) > 0:
                tmpStates = State.merge_c(existingStates, newlyReached, stateOut.nodes())
            if tmpStates.nodes() != allStates.nodes():
                raise Exception("Didn't expect this to happen")

            for st in tmpStates.states:
                allStates.addState(st)

            dur = time.time() - start
            print "state merging took " + str(dur) + " seconds"

        newStates = allStates.states - stateOut.states

        if len(newStates) == 0:
            return State.State(stateOut.nodes())
        elif len(newStates) > maxFinal:
            pdb.set_trace()
            raise Exception("This should have already been caught!")
        elif len(stateOut.nodes()) <= self.__MAX_SIZE:
            return State.State(stateOut.nodes(), newStates)
        else:
            return self.runSingleSAT(allStates.nodes(), st=list(newStates))



    def runSingleSAT(self, outputs, st=None):
        if not self.__dag2cnf:
            print "Precomputing dag2cnf for whole circuit"
            self.__dag2cnf = DAG2CNF.DAG2CNF(self.__sp)
            self.__dag2cnf.cnffile(force=True)

        self.__dag2cnf.setOutputs(outputs)
        self.__dag2cnf.setState(self.__sp.state)

        states = SATInc.runAll(self.__dag2cnf, states=st)
        result = State.State(outputs)
        for state in states:
            result.addState(state)
        return result




    def printGroups(self):
        print "Final output groups:"
        cnt = 0
        for grp in self.__post:
            stOut = self.__flopStatesOut.get(grp)
            if not stOut.full():
                print stOut.annotation(grp)
                cnt += 1

    def printTime(self):
        total = time.time() - self.initTime
        dur   = time.time() - self.start
        print "Run took " + str(dur) + " / " + str(total) + " seconds"


    groups  = property(lambda self: self.__flopGroups)
    states  = property(lambda self: self.__flopStatesOut)


