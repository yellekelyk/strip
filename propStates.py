import Logic2CNF
import myutils
import Netlist
import SAT
import State
import StateProp

import copy
from pygraph.algorithms.searching import depth_first_search

import pdb

a = Netlist.Netlist()
a.readYAML("designs/gates.yml")

# set design here!!
a.readYAML("designs/DestinationDecoder.yml")
a.link("DestinationDecoder")

sp = StateProp.StateProp(a, reset='reset')
(gr, flopGroups) = sp.flopReport()

# set user-specified input constraints here!
userStates = State.State([])


# find iteration order (reverse postorder)
st, pre, post = depth_first_search(gr)
post.reverse()

# initialization code
flopStatesOut = dict()
flopStatesIn = copy.deepcopy(sp.state)
flopStatesIn_p = State.State([])
inputs = dict() 
outToIn = myutils.invert(sp.dag.flopsIn, True)
skip = [False]*len(post)
for group in post:
    flopStatesOut[group] = State.State(flopGroups[group])
    # 'inputs' is mutually exclusive sets of inputs driven from outputs
    inputs[group] = map(outToIn.get, flopGroups[group])
    while None in inputs[group]:
        inputs[group].remove(None)


# start of loop here
# do set comparison to see if input states have changed
while not (flopStatesIn == flopStatesIn_p):
    print "Start of main loop..."
    print "current  state nodes are: " + str(flopStatesIn.nodes())
    print "previous state nodes are: " + str(flopStatesIn_p.nodes())
    print "current  states are: " + str(flopStatesIn.states)
    print "previous states are: " + str(flopStatesIn_p.states)

    # set the inputs here
    # the nodes we care about are in flopStatesIn
    # the states are actually the diff of flopStatesIn and flopStatesIn_p
    # ensure that nodes match for comparison
    #flopStatesIn_p = State.subset(flopStatesIn_p, flopStatesIn.nodes())

    #pdb.set_trace()

    # TODO only use the DIFF of states!
    sp.setInputState(State.merge(userStates, flopStatesIn))

    # save a copy of the initial input state set
    flopStatesIn_p = copy.deepcopy(flopStatesIn)

    # for each state vector
    for group in post:

        if not skip[group]:
            inputSet  = gr.node_attr[group][0]
            outputSet = flopGroups[group]

            print "Considering outputs: " + str(outputSet)

            # TODO : we should only care about non-constant input set
            if len(inputSet) < 16:
                # do simulation to get output states
                print "Running simulation sweep..."
                tt = TruthTable.TruthTable(sp, outputSet)
                states = tt.sweepStates()

            elif len(outputSet) < 12:
                # do SAT
                print "Running SAT..."
                l2cnf = Logic2CNF.Logic2CNF(sp, outputSet)
                states = SAT.runAll(l2cnf, 8)
            else:
                # FrEaK OuTTT!
                raise Exception("Input size is " + str(len(inputSet)) + 
                                " and Output size is " + str(len(outputSet)))

            for st in states:
                flopStatesOut[group].addState(st)

        else:
            print "Skipped " + str(group)
            #flopStatesOut[group] = None
        
    #pdb.set_trace()

    states = []
    # add any new states to cumulative input set
    for group in post:

        # only proceed IF we have less than n/2 states!
        if (len(flopStatesOut[group].states) < 
            2**(len(flopStatesOut[group].nodes())-1)):

            print "Group " + str(group) + " has compressible states"

            # start with existing states for these inputs
            state = State.subset(flopStatesIn, inputs[group])

            # determine the outputs that matter
            outGrp = map(sp.dag.flopsIn.get, inputs[group])

            # add new states implied by outputs
            for st in flopStatesOut[group].states:
                boolVec = map(flopStatesOut[group].getState, 
                              [st]*len(outGrp), outGrp)
                state.addState(myutils.bool2int(boolVec))

        else:
            print "Group " + str(group) + " has too many states, skipping"
            skip[group] = True
            state = State.State(inputs[group])

        states.append(state)

    newStatesIn = reduce(State.merge, states)

    # we should be guaranteed that flopStatesIn.nodes() >= newStatesIn.nodes()

    # remove irrelevant nodes with too many states
    flopStatesIn   = State.subset(flopStatesIn, newStatesIn.nodes())
    #flopStatesIn_p = State.subset(flopStatesIn_p, newStatesIn.nodes())

    # include any new states
    # newSet = set.difference(newStatesIn.states, flopStatesIn.states)
    for st in newStatesIn.states:
        flopStatesIn.addState(st)


# end of while loop
print "Final output groups:"
for grp in flopStatesOut:
    if not skip[grp]:
        print flopStatesOut[grp].nodes()
        print flopStatesOut[grp].states
