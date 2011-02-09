import Logic2CNF
import myutils
import Netlist
import SAT
import SATInc
import State
import StateGroup
import StateProp
import TruthTable

import copy
import glob
import os
from pygraph.algorithms.searching import depth_first_search
import sys
import string

import pdb

#import pexpect


l2cnf_all = dict()

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


def runSingleSAT(sp, outputs, st=None):
    result = State.State(outputs)

    precompute = True

    if precompute:
        if tuple(outputs) not in l2cnf_all:
            print "Precomputing cnf files for : " + str(outputs)
            l2cnf_all[tuple(outputs)] = Logic2CNF.Logic2CNF(sp, outputs)

        l2cnf = l2cnf_all[tuple(outputs)]
        l2cnf.setState(sp.state)
    else:
        l2cnf = Logic2CNF.Logic2CNF(sp, outputs)

    states = SATInc.runAll(l2cnf, states=st)
    #states = SAT.runAll(l2cnf, states=st)
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

        if len(sys.argv) < 2:
            self.print_usage()
            exit(1)

        # set design here!!
        design = sys.argv[1]
        path = 'designs/'

        nl = Netlist.Netlist()
        for infile in glob.glob(os.path.join(path, '*.yml')):
            print "Reading " + infile
            nl.readYAML(infile)
        print "Linking " + design
        nl.link(design)

        print "Building DAG"
        self.__sp = StateProp.StateProp(nl, reset='reset')
        (self.__gr, self.__flopGroups) = self.__sp.flopReport()

        # set user-specified input constraints here!
        self.__userStates = State.State([])


        # find iteration order (reverse postorder)
        st, pre, self.__post = depth_first_search(self.__gr)
        self.__post.reverse()

        # initialization code
        # description of data members
        # flopStatesOut: maps group->(State for all outputs)
        # flopStatesIn: aggregated input state combinations for fixed inputs
        # flopStatesIn_p: previous version of flopStatesIn
        # inputs: maps group output -> constrained input
        # flopsIn: maps group -> constrained inputs
        self.__flopStatesOut = StateGroup.StateGroup()
        #self.__flopStatesIn = copy.deepcopy(self.__sp.state)
        #self.__flopStatesIn_p = State.State(self.__flopStatesIn.nodes())
        self.__flopStatesIn_p = dict()
        self.__inputs = dict() 
        self.__flopsIn = dict()
        outToIn = myutils.invert(self.__sp.dag.flopsIn, True)
        #self.__skip = [False]*len(self.__post)
        self.__outToIn = outToIn
        for group in self.__post:
            self.__inputs[group] = map(outToIn.get, self.__flopGroups[group])
            while None in self.__inputs[group]:
                self.__inputs[group].remove(None)
            reset_in  = State.subset(self.__sp.state, self.__inputs[group])
            reset_out = State.rename(reset_in, self.__sp.dag.flopsIn)
            self.__flopStatesOut.insert(group, reset_out)

            flopsIn = set.intersection(set(self.__gr.node_attr[group][0]), 
                                       set(self.__sp.dag.flopsIn.keys()))
            self.__flopsIn[group] = flopsIn
            self.__flopStatesIn_p[group] = State.State(flopsIn)



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
                (updated, inputs) = self.checkInputs(group)
                #pdb.set_trace()
                if updated:
                    # mark a global update
                    ret = True
                    # updates the outputs for group
                    self.runGroup(group, inputs)
                    # updates all inputs from group
                    #self.updateInputs(group)


            # check if we should garbage collect
            # this means we can remove this group from l2cnf_all to
            # save on memory
            if self.__flopStatesOut.get(group).full():
                outputs = tuple(self.__flopGroups[group])
                if outputs in l2cnf_all:
                    print "Garbage collecting l2cnf_all: " + str(outputs)
                    l2cnf_all.pop(outputs)

        return ret

    def checkInputs(self, group):
        "checks to see if group has any new input constraints"
        
        # these are ALL inputs for this group
        #inputSet  = self.__gr.node_attr[group][0]
        # these are ALL flop inputs for the circuit
        #inputFlops = self.__sp.dag.flopsIn.keys()

        # these are ALL flop inputs for the current group
        flopsIn = self.__flopsIn[group]

        # lookup the previous input state for this group
        inStates_p = self.__flopStatesIn_p[group]

        # calculate the current input state for this group
        flopsOut = map(self.__sp.dag.flopsIn.get, flopsIn)
        inStates = State.rename(self.__flopStatesOut.toState(flopsOut),
                                self.__outToIn)

        updated = True
        # determine if anything has been updated
        if set(inStates.nodes()) == set(inStates_p.nodes()):
            if inStates == inStates_p:
                updated = False
        else:
            inStates_p = State.State(list(inStates.nodes()))

        # calculate state diff
        diffStates = State.State(list(inStates.nodes()))
        for st in set.difference(inStates.states, inStates_p.states):
            diffStates.addState(st)

        print str(str(group) + ": There were " + 
                  str(len(self.__flopStatesIn_p[group].nodes())-
                      len(inStates.nodes())) + 
                  " input constraints dropped")      

        print str(str(group) + ": Considering " + str(len(diffStates.states)) + 
                  " new input states")


        # set previous state
        self.__flopStatesIn_p[group] = inStates

        return (updated, diffStates)


    #def updateInputs(self, group):
    #    "Update the constant inputs associated with group outputs"
    #    
    #    stOut = self.__flopStatesOut.get(group)
    #
    #    if self.__skip[group]:
    #        # remove all inputs associated with this group
    #        self.__removeInputNodes__(group)
    #    else:
    #        # check number of states
    #        # only proceed IF we have less than 2**n states!
    #        if stOut.full():
    #            print "Group " + str(group) + " has too many states, skipping"
    #            # remove all inputs associated with this group
    #            self.__skip[group] = True
    #            self.__removeInputNodes__(group)
    #        else:
    #            print "Group " + str(group) + " has compressible states"
    #
    #            # start with existing states for these inputs
    #            # todo consider maintaining a map of these states
    #            # instead of constantly subsetting/merging
    #            state = State.subset(self.__flopStatesIn, self.__inputs[group])
    #
    #            # determine the outputs that matter
    #            outGrp = map(self.__sp.dag.flopsIn.get, self.__inputs[group])
    #
    #            # add new states implied by outputs
    #            for st in stOut.states:
    #                boolVec = map(stOut.getState, [st]*len(outGrp), outGrp)
    #                state.addState(myutils.bool2int(boolVec))
    #
    #            # merge new states into flopStatesIn
    #            self.__mergeInputState__(group, state)


    def __removeInputNodes__(self, group):
        " Ensures the input state doesn't have any input in it"
        #self.__flopStatesIn_p[group] = copy.deepcopy(self.__flopStatesIn)
        self.__flopStatesIn_p[group] = State.subset(self.__flopStatesIn,
                                                    self.__inputs[group])
        nodes = list(self.__flopStatesIn.nodes())
        for node in self.__inputs[group]:
            if node in nodes:
                nodes.remove(node)
        self.__flopStatesIn = State.subset(self.__flopStatesIn, nodes)

    def __mergeInputState__(self, group, state):
        #self.__flopStatesIn_p = copy.deepcopy(self.__flopStatesIn)
        self.__flopStatesIn_p[group] = State.subset(self.__flopStatesIn,
                                                    self.__inputs[group])
        subsetNodes =[]
        for node in self.__flopStatesIn.nodes():
            if node not in state.nodes():
                subsetNodes.append(node)
        subset = State.subset(self.__flopStatesIn, subsetNodes)
        self.__flopStatesIn = State.merge(subset, state)


    def runGroup(self, group, inputs):
        "Run one pass for group, using inputs as state diff"

        statesOut = self.__flopStatesOut.get(group)
        if statesOut.full():
            #if self.__skip[group]:
            raise Exception("Shouldn't call if skip is true!")

        inputSet  = self.__gr.node_attr[group][0]
        outputSet = self.__flopGroups[group]

        print "Considering outputs: " + str(outputSet)
        constIn = list(set.intersection(inputSet, set(inputs.nodes())))

        # find number of inputs that we effectively have to sweep
        inputCombos = 2**(len(inputSet)-len(constIn)) + len(inputs.states)

        # find number of outputs that haven't been SATISFIED
        outputCombos = 2**(len(outputSet))-len(statesOut.states)

        #pdb.set_trace()

        # set relevant constant inputs before running
        self.__sp.setInputState(State.merge(self.__userStates, inputs))

        #pdb.set_trace()

        # TODO: stop simulation/SAT sweep early if > half states seen
        if inputCombos < 2**16:
            # do simulation to get output states
            print "Running simulation sweep..."
            tt = TruthTable.TruthTable(self.__sp, outputSet)
            states = tt.sweepStates()
            
        elif outputCombos < 2**12:

            # do SAT
            print "Running SAT..."
            
            #l2cnf = Logic2CNF.Logic2CNF(sp, outputSet)
            #states = SAT.runAll(l2cnf)
            #states = runHierSAT(sp, outputSet)
            outputStates = list(set.difference(set(range(2**len(outputSet))), 
                                               statesOut.states))

            #pdb.set_trace()
            states = runSingleSAT(self.__sp, outputSet, st=outputStates).states

            #if outputCombos <= 128:
            #states = runSingleSAT(self.__sp, outputSet, st=outputStates).states
                               
                           
            #else:
            #    # attempt to 'prune' problem before sweeping
            #    states = runIterSAT(self.__sp, outputSet).states

        else:
            # FrEaK OuTTT!
            print (str("Skipping b/c input combos are " + str(inputCombos) +
                       " and Output size is " + str(len(outputSet))))
            states = set()
            #self.__skip[group] = True
            statesOut.setSkip()

        print "reached states: " + str(states)

        #pdb.set_trace()

        for st in states:
            statesOut.addState(st)

        #if self.__flopStatesOut.get(group).full():
        #    print str(group) + " : Outputs are full, setting skip"
        #    self.__skip[group] = True



    def printGroups(self):
        print "Final output groups:"
        for grp in self.__post:
            stOut = self.__flopStatesOut.get(grp)
            if not stOut.full():
                stateList = list(stOut.states)
                stateList.sort()
                idx = range(len(stateList))
                stateStr = map(lambda x,y:"S"+str(x)+"="+str(y), idx, stateList)
                stateStr = reduce(lambda x,y: x + " " + y, stateStr)
                print str("set_fsm_state_vector {" + 
                          string.join(stOut.nodes()) + "}")
                print str("set_fsm_encoding {" + stateStr + "}")

    def print_usage(self):
        print "Usage: python propStates.py <moduleName>"

    groups  = property(lambda self: self.__flopGroups)


#if len(sys.argv) < 2:
#    print "Usage: python propStates.py <moduleName>"
#    exit(1)
#
## set design here!!
#design = sys.argv[1]
#
## set path here!!
#path = 'designs/'
#
#a = Netlist.Netlist()
#for infile in glob.glob(os.path.join(path, '*.yml')):
#    print "Reading " + infile
#    a.readYAML(infile)
#
#print "Linking " + design
#a.link(design)
#
#print "Building DAG"
#sp = StateProp.StateProp(a, reset='reset')
#(gr, flopGroups) = sp.flopReport()
#
## set user-specified input constraints here!
#userStates = State.State([])
#
#
## find iteration order (reverse postorder)
#st, pre, post = depth_first_search(gr)
#post.reverse()
#
## initialization code
#flopStatesOut = dict()
#flopStatesIn = copy.deepcopy(sp.state)
#flopStatesIn_p = State.State(flopStatesIn.nodes())
#inputs = dict() 
#outToIn = myutils.invert(sp.dag.flopsIn, True)
#skip = [False]*len(post)
#for group in post:
#    flopStatesOut[group] = State.State(flopGroups[group])
#    # 'inputs' is mutually exclusive sets of inputs driven from outputs
#    inputs[group] = map(outToIn.get, flopGroups[group])
#    while None in inputs[group]:
#        inputs[group].remove(None)


# start of loop here
# do set comparison to see if input states have changed
#while not (flopStatesIn == flopStatesIn_p):
#    print "Start of main loop..."
#    print "current state nodes are: " + str(flopStatesIn.nodes())
#    print "previous state nodes are: " + str(flopStatesIn_p.nodes())
#    #print "current states are: " + str(flopStatesIn.states)
#    #print "previous states are: " + str(flopStatesIn_p.states)
#
#    # set the inputs here
#    # only use the DIFF of states!
#    # we're guaranteed that flopStatesIn_p.nodes() >= flopStatesIn.nodes()
#    diffNodesIn = set.difference(set(flopStatesIn_p.nodes()),
#                                 set(flopStatesIn.nodes()))
#    flopStatesIn_p = State.subset(flopStatesIn_p, flopStatesIn.nodes())
#    diffStatesIn = State.State(flopStatesIn.nodes())
#    for diff in set.difference(flopStatesIn.states, flopStatesIn_p.states):
#        diffStatesIn.addState(diff)
#
#    sp.setInputState(State.merge(userStates, diffStatesIn))
#
#    # for each state vector
#    for group in post:
#
#        if not skip[group]:
#            inputSet  = gr.node_attr[group][0]
#            outputSet = flopGroups[group]
#
#            print "Considering outputs: " + str(outputSet)
#            constIn = list(set.intersection(inputSet,set(flopStatesIn.nodes())))
#
#            
#            updated = True
#            # some stateful nodes might have been relaxed
#            if len(set.intersection(diffNodesIn, inputSet)) == 0:
#                print "Input node set hasn't changed"
#                updated = False
#            if not updated:
#                newStates = State.subset(diffStatesIn, constIn)
#                oldStates = State.subset(flopStatesIn_p, constIn)
#
#                if newStates != oldStates:
#                    updated = True
#
#            #pdb.set_trace()
#            if not updated:
#                #statesInPrev == statesIn:
#                print "Input states haven't changed, no need to run sweep"
#            else:
#
#                # we really only care about non-constant input set
#                if len(inputSet)-len(constIn) < 16:
#                    # do simulation to get output states
#                    # TODO: stop simulation early if > half states seen
#                    print "Running simulation sweep..."
#                    tt = TruthTable.TruthTable(sp, outputSet)
#                    states = tt.sweepStates()
#
#                elif len(outputSet) < 12:
#                    # do SAT
#                    print "Running SAT..."
#                    #l2cnf = Logic2CNF.Logic2CNF(sp, outputSet)
#                    #states = SAT.runAll(l2cnf)
#                    #states = runHierSAT(sp, outputSet)
#                    states = runIterSAT(sp, outputSet)
#                else:
#                    # FrEaK OuTTT!
#                    print str("Skipping b/c input size is " + str(len(inputSet)) + 
#                              " and Output size is " + str(len(outputSet)))
#                    states = set()
#                    skip[group] = True
#                    # TODO: try breaking outputs running SAT, combining ?
#                    #raise Exception("Input size is " + str(len(inputSet)) + 
#                    #                " and Output size is " + str(len(outputSet)))
#
#                for st in states:
#                    flopStatesOut[group].addState(st)
#
#        else:
#            print "Skipped " + str(group)
#            #flopStatesOut[group] = None
#        
#    #pdb.set_trace()
#
#    states = []
#    # add any new states to cumulative input set
#    # todo add them as we go (should be more efficient)
#    for group in post:
#
#        # only proceed IF we have less than n/2 states!
#        if (len(flopStatesOut[group].states) < 
#            2**(len(flopStatesOut[group].nodes())-1)) and not skip[group]:
#
#            print "Group " + str(group) + " has compressible states"
#
#            # start with existing states for these inputs
#            state = State.subset(flopStatesIn, inputs[group])
#
#            # determine the outputs that matter
#            outGrp = map(sp.dag.flopsIn.get, inputs[group])
#
#            # add new states implied by outputs
#            for st in flopStatesOut[group].states:
#                boolVec = map(flopStatesOut[group].getState, 
#                              [st]*len(outGrp), outGrp)
#                state.addState(myutils.bool2int(boolVec))
#
#        else:
#            print "Group " + str(group) + " has too many states, skipping"
#            skip[group] = True
#            state = State.State(inputs[group])
#
#        states.append(state)
#
#    #pdb.set_trace()
#
#    newStatesIn = reduce(State.merge, states)
#
#    # save a copy of the previous input state set
#    flopStatesIn_p = copy.deepcopy(flopStatesIn)
#
#
#    # we should be guaranteed that flopStatesIn.nodes() >= newStatesIn.nodes()
#    # remove irrelevant nodes with too many states
#    flopStatesIn   = State.subset(flopStatesIn, newStatesIn.nodes())
#    #flopStatesIn_p = State.subset(flopStatesIn_p, newStatesIn.nodes())
#
#    # include any new states
#    # newSet = set.difference(newStatesIn.states, flopStatesIn.states)
#    for st in newStatesIn.states:
#        flopStatesIn.addState(st)

fs = FindStates()
fs.run()
fs.printGroups()



