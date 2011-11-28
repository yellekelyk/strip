import DC
import Logic2CNF
import DAG2CNF
import InputFSMs
import myutils
import Netlist
import SAT
import SATInc
import State
import StateSuperset
import StateGroup
import StateProp
import TruthTable

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


#l2cnf_all = dict()
dag2cnf = None


def runHierSAT(sp, outputs):
    "Run a SAT sweep in a recursive hierarchical fashion"

    print "runHierSAT called with outputs= " + str(outputs)

    if len(outputs) <= 4:
        l2cnf = Logic2CNF.Logic2CNF(sp, outputs)
        states = SAT.runAll(l2cnf)
        return states
    else:
        outputs1 = outputs[0:(len(outputs)/2)]
        outputs2 = outputs[(len(outputs)/2):len(outputs)]

        run1 = runHierSAT(sp, outputs1)
        run2 = runHierSAT(sp, outputs2)
        
        # do reduction step of combining states
        if len(run1)*len(run2) >= 2**12:
            #this is too large to sweep, throw our hands up in the air
            # maybe return None to indicate this ???
            raise Exception("tooo many states to sweep !!")
        else:
           state1 = State.State(outputs1) 
           state2 = State.State(outputs2) 
           for st in run1:
               state1.addState(st)
           for st in run2:
               state2.addState(st)
           state = State.merge(state1, state2)
           stateList = list(state.states)
           stateList.sort()

           print str("Running reduction sweep on " + str(len(stateList)) + 
                     " states: " + str(stateList))

           #pdb.set_trace()
           if state.nodes() != list(outputs):
               raise Exception("I expect these to be the same!!")

           l2cnf = Logic2CNF.Logic2CNF(sp, outputs)
           states = SAT.runAll(l2cnf, states=stateList)
           return states

#def runSAT_no_overlap(sp, stateOut, maxSize=12):
#    """ Run SAT on all states; if there are too many states then 
#    we attempt to prune some of the possibilties first and only run on the 
#    remainder 
#
#    stateOut is a State object; 
#    we want to run on 2**len(stateOut.nodes())-stateOut.states() possibilities
#
#    """
#
#    newStates = []
#    numNewStates = 0
#
#    #maxFinal = 2**maxSize
#    maxFinal = 2**18
#
#    allStates = copy.deepcopy(stateOut)
#
#    if len(stateOut.nodes()) == 4:
#        #pdb.set_trace()
#        pass
#
#    for newNodes in myutils.chunker(stateOut.nodes(), maxSize):
#
#        #if len(stateOut.nodes()) > 2000:
#        #    pdb.set_trace()
#
#        start = time.time()
#
#        #newState        = State.subset(allStates, newNodes)
#        #existingStates  = State.subset(allStates, list(set(allStates.nodes())-set(newNodes)))
#        newState, existingStates = State.subset_c(allStates, newNodes)
#
#        dur = time.time() - start
#        print "state separation took " + str(dur) + " seconds"
#
#
#        statesToSweep = list(newState.not_states)
#        if len(statesToSweep) > 0:
#            newlyReached = runSingleSAT(sp, newState.nodes(), st=statesToSweep)
#        else:
#            newlyReached = State.State(newState.nodes())
#        
#        if newlyReached < 2**10:
#            print "reached interim states: " + str(newlyReached.states)
#        else:
#            print "reached interim states: (hidden)"
#
#        #pdb.set_trace()
#
#        numNewStates += len(existingStates.states) * len(newlyReached.states)
#
#        if numNewStates > maxFinal:
#            print "We just reached " + str(numNewStates) + " to test, I quit"
#            return None
#        else:
#            start = time.time()
#            for st in newlyReached.states:
#                newState.addState(st)
#            #allStates = State.merge_c(existingStates, newState, stateOut.nodes())
#            tmpStates = State.State(stateOut.nodes())
#            if len(newlyReached.states) > 0:
#                tmpStates = State.merge_c(existingStates, newlyReached, stateOut.nodes())
#            if tmpStates.nodes() != allStates.nodes():
#                raise Exception("Didn't expect this to happen")
#
#            for st in tmpStates.states:
#                allStates.addState(st)
#
#            dur = time.time() - start
#            print "state merging took " + str(dur) + " seconds"
#
#    newStates = allStates.states - stateOut.states
#
#    if len(newStates) == 0:
#        return State.State(stateOut.nodes())
#    elif len(newStates) > maxFinal:
#        pdb.set_trace()
#        raise Exception("This should have already been caught!")
#    else:
#        return runSingleSAT(sp, allStates.nodes(), st=list(newStates))
#    #    newStates.append(newlyReached)
#
#    #origStates = map(lambda x: State.subset(stateOut, 
#    #                                        list(set(stateOut.nodes())-
#    #                                             set(x.nodes()))), newStates)
#
#    #reducedPossibilities = reduce(lambda x,y: x*y, 
#    #                              map(lambda x: len(x.states), newStates))
#
#    #reducedPossibilities = map(lambda x,y: len(x.states)*len(y.states), newStates, origStates)
#
#    
#
#
#    #if reducedPossibilities > 2**12:
#    #    print "There are " + str(reducedPossibilities) + " left to check ... I quit!"
#    #    return None
#    #
#    #else:
#    #    # combine them back into one large state, and then sweep possibilities
#    #    # to prune even more
#    #    newState = reduce(State.mergeKeep, newStates)
#    #    if len(newState.states) > 0:
#    #        return runSingleSAT(sp, newState.nodes(), st=list(newState.states))
#    #    else:
#    #        return newState


def runSAT(sp, stateOut, maxSize=12, overlap=0):
    """ Run SAT on all states; if there are too many states then 
    we attempt to prune some of the possibilties first and only run on the 
    remainder 

    stateOut is a State object; 
    we want to run on 2**len(stateOut.nodes())-stateOut.states() possibilities

    """

    newStates = []
    numNewStates = 0

    #maxFinal = 2**maxSize
    maxFinal = 2**18

    allStates = copy.deepcopy(stateOut)

    for newNodes in myutils.chunker_ol(stateOut.nodes(), maxSize, overlap):

        start = time.time()

        newState, existingStates = State.subset_c(allStates, newNodes)

        dur = time.time() - start
        print "state separation took " + str(dur) + " seconds"


        statesToSweep = list(newState.not_states)
        if len(statesToSweep) > 0:
            newlyReached = runSingleSAT(sp, newState.nodes(), st=statesToSweep)
        else:
            newlyReached = State.State(newState.nodes())
        
        if len(newlyReached.states) < 2**9:
            print "reached interim states: " + str(newlyReached.states)
        else:
            print "reached interim states: (hidden for length)"

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

        #numNewStates = len(allStates.states-stateOut.states)
        #if numNewStates > maxFinal:
        #    print "We just reached " + str(numNewStates) + " to test, I quit"
        #    return None

        dur = time.time() - start
        print "state merging took " + str(dur) + " seconds"


    newStates = allStates.states - stateOut.states

    if len(newStates) == 0:
        return State.State(stateOut.nodes())
    elif len(newStates) > maxFinal:
        pdb.set_trace()
        raise Exception("This should have already been caught!")
    else:
        return runSingleSAT(sp, allStates.nodes(), st=list(newStates))



def runSingleSAT(sp, outputs, st=None):
    global dag2cnf

    if not dag2cnf:
        print "Precomputing dag2cnf for whole circuit"
        dag2cnf = DAG2CNF.DAG2CNF(sp)
        dag2cnf.cnffile(force=True)

    dag2cnf.setOutputs(outputs)
    dag2cnf.setState(sp.state)

    states = SATInc.runAll(dag2cnf, states=st)
    result = State.State(outputs)
    for state in states:
        result.addState(state)
    return result


def runIterSAT(sp, outputs, group=6, step=1):
    "Run a SAT sweep; preprocess by running smaller subset sweeps first"

    print "runIterSAT called with outputs= " + str(outputs)

    if len(outputs) < group:
        group = len(outputs)
    nRuns = 1 + (len(outputs)-group)/step

    # produce a list of output subsets
    subsets = map(lambda x:list(outputs[(x*step):(x*step+group)]), range(nRuns))
    states = map(runSingleSAT,[sp]*len(subsets),subsets)
    allStates = reduce(State.merge, states)

    stateList = list(allStates.states)
    stateList.sort()

    if len(stateList) >= 2**12:
        #this is too large to sweep, throw our hands up in the air
        # maybe return None to indicate this ???
        raise Exception("tooo many states to sweep !!")
    else:
        print str("Running reduction sweep on " + str(len(stateList)) + 
                  " states: " + str(stateList))

        if allStates.nodes() != list(outputs):
            raise Exception("I expect these to be the same!!")
        #pdb.set_trace()
        #l2cnf = Logic2CNF.Logic2CNF(sp, outputs)
        #states = SAT.runAll(l2cnf, states=stateList)
        states = runSingleSAT(sp, outputs, states=stateList)
        return states


class FindStates:
    def __init__(self, debug=0):

        self.__debug = debug
        self.start = time.time()

        if len(sys.argv) < 2:
            self.print_usage()
            exit(1)

        # set design here!!
        design = sys.argv[1]
        path = 'designs.protocol/'

        nl = Netlist.Netlist()
        for infile in glob.glob(os.path.join(path, '*.yml')):
            print "Reading " + infile
            nl.readYAML(infile)
        print "Linking " + design
        nl.link(design)

        print "Building DAG"
        if 'reset' in nl.mods[design].ports:
            reset = 'reset'
        elif 'Reset' in nl.mods[design].ports:
            reset = 'Reset'
        else:
            raise Exception("Couldn't find reset signal")
        
        fsms = InputFSMs.InputFSMs(nl)
        for i in range(2, len(sys.argv)):
            fsms.readYAML(sys.argv[i])

        self.__sp = StateProp.StateProp(nl, reset, fsms.protocols())

        self.__MAX_SIZE=14


        print "Finding Flops"
        (self.__gr, self.__flopGroups) = self.__sp.flopReport()
        #(self.__gr, self.__flopGroups) = self.__sp.flopReport(self.__MAX_SIZE)
        # todo consider phasing out private data member 
        # self.__flopGroups, since it becomes redundant once
        # we have created self.__flopStatesOut below
        # self.__flopGroups[grp] == self.__flopStatesOut.lookup(grp).nodes()


        # DIFFERENCE for protocol
        #supersets = self.__combineGroupsByStr__("_capacity_")
        supersets = self.__combineGroupsByStr__("fifo_capacity_")
        #supersets = self.__combineGroupsByStr__("_valid_")
        #supersets = self.__combineGroupsByStr__("_state_")
        #supersets = set()

        if self.__debug > 0:
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
        self.__flopGroups.append(tuple(ss.nodes()))

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
                states = runSAT(self.__sp, stateOut, self.__MAX_SIZE, overlap=8)
                #states = runSAT_no_overlap(self.__sp, stateOut, self.__MAX_SIZE)

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
                print "reached states: " + str(states)
            else:
                print "reached states: (hidden for length)"

            for st in states:
                stateOut.addState(st)


    def printGroups(self):
        print "Final output groups:"
        cnt = 0
        for grp in self.__post:
            stOut = self.__flopStatesOut.get(grp)
            if not stOut.full():
                print stOut.annotation(grp)
                cnt += 1

    def printTime(self):
        dur = time.time() - self.start
        print "Run took " + str(dur) + " seconds"


    def print_usage(self):
        print "Usage: python FindStates.py <moduleName> [inputConstraintFile]"

    groups  = property(lambda self: self.__flopGroups)
    states  = property(lambda self: self.__flopStatesOut)

fs = FindStates()
gc.disable()
fs.run()
fs.printTime()
fs.printGroups()
gc.enable()
