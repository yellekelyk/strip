import Netlist
import StateProp
import State
import utils

a = Netlist.Netlist()
a.readYAML("designs/gates.yml")
#a.readYAML("designs/test7.yml")
#a.link("test7")

a.readYAML("designs/PktDestDecoder.yml")
a.link("PktDestDecoder")

s = StateProp.StateProp(a)

# choose flops for output here
flops      = s.flops.keys()
flops.sort()
flops.reverse()

# pull this info out for later use
flopsIn = dict()

for k in s._StateProp__dag.flopsIn:
    flopsIn[s._StateProp__dag.flopsIn[k]] = k


# do first pass
s.propSims()
states = s.getStateSet(flops)


prevStates = set()

while len(prevStates) != len(states):

    # now do second pass
    flopsInList = []

    for flop in flops:
        flopsInList.append(flopsIn[flop])
    st = State.State(flopsInList)

    #for state in states:
    for state in set.difference(states, prevStates):
        st.addState(state)

    # remake object (this is inefficient, meh)
    s = StateProp.StateProp(a, fixFlopInput=False)
    s.annotateState(st)
    s.propSims()
    prevStates = states
    states = set.union(states, s.getStateSet(flops))


print "Finished: states=" + str(states)
