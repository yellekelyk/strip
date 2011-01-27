import Netlist
import StateProp
import State
import re
import difflib
import copy

def flopSet(flopsIn):
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



a = Netlist.Netlist()
a.readYAML("designs/gates.yml")
#a.readYAML("designs/test7.yml")
#a.link("test7")

a.readYAML("designs/PktDestDecoder.yml")
a.link("PktDestDecoder")

s = StateProp.StateProp(a, reset='reset')

# choose flops for output here
flops = list(s.dag.flops)
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
    s = StateProp.StateProp(a)
    s.annotateState(st)
    s.propSims()
    prevStates = states
    states = set.union(states, s.getStateSet(flops))


print "Finished: states=" + str(states)
