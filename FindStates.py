import DC
import Logic2CNF
import DAG2CNF
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
        if 'reset' in nl.mods[design].ports:
            reset = 'reset'
        elif 'Reset' in nl.mods[design].ports:
            reset = 'Reset'
        else:
            raise Exception("Couldn't find reset signal")

        self.__sp = StateProp.StateProp(nl, reset)

        print "Finding Flops"
        (self.__gr, self.__flopGroups) = self.__sp.flopReport()

        # set user-specified input constraints here!
        self.__userStates = StateGroup.StateGroup()

        # TEST CODE!####
        #asdf = State.State(['in[3]','in[2]','in[1]','in[0]'])
        #asdf.addState(1)
        #asdf.addState(2)
        #asdf.addState(4)
        #asdf.addState(8)
        #self.__userStates.insert(-1, asdf)

        # END TEST CODE!###


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
            reset_in  = State.subset(self.__sp.state, self.__inputs[group])
            reset_out = State.rename(reset_in, self.__sp.dag.flopsIn)
            self.__flopStatesOut.insert(group, reset_out)

            flopsIn = set.intersection(set(self.__gr.node_attr[group][0]), 
                                       set(self.__sp.dag.flopsIn.keys()))
            self.__flopsIn[group] = flopsIn
            self.__cnt[group] = 0

        # create empty flopStatesIn_p for each group
        for group in self.__post:
            inGrps = dict()
            for flop in self.__flopsIn[group]:
                # get output node
                flopOut = self.__sp.dag.flopsIn[flop]
                
                # lookup group associated with this node
                key = self.__flopStatesOut.lookup(flopOut)
                if not key in inGrps:
                    inGrps[key] = []
                inGrps[key].append(flop)
            sg = StateGroup.StateGroup()            
            for key in inGrps:
                inGrps[key].sort()
                inGrps[key].reverse()
                sg.insert(key, State.State(inGrps[key]))
            self.__flopStatesIn_p[group] = sg


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
                #asdf = {'self':self, 'group':group, 
                #        'updated':None, 'inputs':None}
                #cProfile.runctx('(updated, inputs) = self.checkInputs(group)', globals(), asdf)
                #updated = asdf['updated']
                #inputs  = asdf['inputs']

                (updated, inputs) = self.checkInputs(group)
                
                #pdb.set_trace()

                dur = time.time() - start
                print "checkInputs() took " + str(dur) + " seconds"
              
                #if dur > 1:
                #    exit(1)


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

        # calculate state diff
        #diffStates = State.State(list(inStates.nodes()))
        #for st in set.difference(inStates.states, inStates_p.states):
        #    diffStates.addState(st)
        #if group == 10:
        #   pdb.set_trace()

        #if group == 5:
        #   pdb.set_trace()

        diffStates = inStates.diff(inStates_p)

        print str(str(group) + ": There were " + 
                  str(len(self.__flopStatesIn_p[group].nodes())-
                      len(inStates.nodes())) + 
                  " input constraints dropped")      

        #print str(str(group) + ": Considering " + str(len(diffStates.states))  
        # " new input states")


        # set previous state
        self.__flopStatesIn_p[group] = inStates

        return (updated, diffStates)


    def runGroup(self, group, inputs):
        "Run one pass for group, using inputs as state diff"

        statesOut = self.__flopStatesOut.get(group)
        if statesOut.full():
            raise Exception("Shouldn't call if skip is true!")

        inputSet  = self.__gr.node_attr[group][0]
        outputSet = self.__flopGroups[group]

        print "Considering outputs: " + str(outputSet)
        constIn = list(set.intersection(inputSet, set(inputs.nodes())))

        # find number of inputs that we effectively have to sweep
        #inputCombos = 2**(len(inputSet)-len(constIn)) + len(inputs.states)
        inputCombos = 2**(len(inputSet)-len(constIn)) + inputs.numStates()

        # find number of outputs that haven't been SATISFIED
        outputCombos = 2**(len(outputSet))-len(statesOut.states)

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

        # TODO: stop simulation/SAT sweep early if > half states seen
        # TODO: avoid TT simulation if logic cone is large 
        if inputCombos < 2**16:
            # do simulation to get output states
            print "Running simulation sweep..."
            tt = TruthTable.TruthTable(self.__sp, outputSet)
            states = tt.sweepStates()
            
        elif outputCombos < 2**13:

            # do SAT
            print "Running SAT..."
            
            outputStates = list(set.difference(set(range(2**len(outputSet))), 
                                               statesOut.states))

            states = runSingleSAT(self.__sp, outputSet, st=outputStates).states


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


    def printGroups(self):
        print "Final output groups:"
        cnt = 0
        for grp in self.__post:
            stOut = self.__flopStatesOut.get(grp)
            if not stOut.full():
                print stOut.dcPrint()
                cnt += 1


    def print_usage(self):
        print "Usage: python FindStates.py <moduleName>"

    groups  = property(lambda self: self.__flopGroups)
    states  = property(lambda self: self.__flopStatesOut)

fs = FindStates()
gc.disable()
fs.run()
gc.enable()
#fs.printGroups()
DC.DC(fs.states)



