import State
import pdb

class StateGroup:
    "A class that holds a group of State objects"
    def __init__(self):
        self.__inputs = dict()
        self.__states = dict()

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

    def toState(self, nodes):
        "do a merge of all necessary states, ignoring those that are full"
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
      
