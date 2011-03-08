import State
import pdb

class StateGroup:
    "A class that holds a group of State objects"
    def __init__(self):
        self.__inputs = dict()
        self.__states = dict()

    def initGroups(self, sg):
        """ Initialize using the same node groupings, but assume no states """
        tmpStates = sg.states()
        for key in tmpStates:
            self.insert(key, State.State(tmpStates[key].nodes()))

    def __eq__(self, sg):
        return self.states() == sg.states()
    
    def __ne__(self, sg):
        return not (self.__eq__(sg))

    def grpEq(self, sg):
        grpEq  = set(self.states().keys()) == set(sg.states().keys())
        if grpEq:
            for key in self.states():
                if set(self.states()[key].nodes()) != set(sg.states()[key].nodes()):
                    grpEq = False
                    break
        return grpEq

    def insert(self, key, state):
        for node in state.nodes():
            # state objects MUST be mutually exclusive!
            if node in self.__inputs:
                raise Exception("Attempt to add state with node " + node)

        for node in state.nodes():
            self.__inputs[node] = (state, key)
        self.__states[key] = state

    def get(self, key):
        return self.__states[key]

    def lookup(self, node):
        return self.__inputs[node][1]

    def nodes(self):
        return self.__inputs.keys()

    def states(self):
        return self.__states

    def numStates(self):
        numStates = 1
        for grp in self.states():
            numStates *= len(self.states()[grp].states)
        return numStates


    def rename(self, conversion):
        """ Uses conversion to rename all nodes """
        sg = StateGroup()
        for key in self.__states:
            st = State.rename(self.__states[key], conversion)
            sg.insert(key, st)
        return sg


    def subset(self, nodes):
        """ Returns a copy of StateGroup, only keeping nodes """
        keys = dict()
        for node in nodes:
            if not node in self.__inputs:
                raise Exception("node not in StateGroup: " + node)
            (state, key) = self.__inputs[node]
            if key not in keys:
                keys[key] = []
            keys[key].append(node)
            
        sg = StateGroup()
        for key in keys:
            sg.insert(key, State.subset(self.__states[key], keys[key]))

        return sg


    def diff(self, sg):
        """ Returns a state group diff """
        if not self.grpEq(sg):
            raise Exception("Diff needs to have same nodes/groups!")

        diff = StateGroup()
        for grp in self.states():
            state  = State.State(self.states()[grp].nodes())
            st1 = self.states()[grp].states
            st2 = sg.states()[grp].states
            diffSt = set.difference(st1, st2)
            if len(diffSt) == 0:
                diffSt = st1
            for st in diffSt:
                state.addState(st)

            diff.insert(grp, state)
        return diff


    def toState(self, nodes):
        "do a merge of all necessary states, ignoring those that are full"
        raise Exception("This is deprecated!")
        keys = set()
        keys2nodes = dict()
        for node in nodes:
            pair = self.__inputs[node]
            state = pair[0]
            key = pair[1]
            keys.add(key)
            if key not in keys2nodes:
                keys2nodes[key] = []
            keys2nodes[key].append(node)
        
        stateAll = State.State([])
        for key in keys:
            state = self.get(key)
            if not state.full():
                stateAll = State.merge(stateAll, 
                                       State.subset(state, keys2nodes[key]))

        return stateAll
      
