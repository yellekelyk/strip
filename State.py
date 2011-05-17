import myutils
import copy
import pdb
import string

class State:
    "Generic state information for a group of nodes"
    def __init__(self, nodes):
        self.__states = set()
        self.__nodes = nodes
        self.__skip = False

    def __eq__(self, state):
        ret = False
        if set(state.nodes()) == set(self.__nodes):
            tmp = subset(state, self.__nodes)
            ret = self.__states == tmp.states
        return ret

    def __ne__(self, state):
        return not self.__eq__(state)

    def full(self):
        #return len(self.__states) > 2**(len(self.__nodes)-1) or self.__skip
        return len(self.__states) == self.numAllStates() or self.__skip

    def numAllStates(self):
        return 2**len(self.__nodes)

    def numStates(self):
        return len(self.__states)

    def setSkip(self):
        self.__skip = True
        
    def subgroups(self):
        return [self]

    def addState(self, state):
        if type(state) == type(0) or type(state) == type(0l):
            self.__addNumState__(state)
        elif type(state) == type(""):
            self.__addStrState__(state)
        else:
            raise TypeError("Bad type received: " + str(type(state)))

    def getState(self, state, node):
        if state not in self.__states:
            raise Exception("state " + str(state) + " not in set of states")
        shift = len(self.__nodes) - 1 - self.__nodes.index(node)
        return bool(state & (1 << shift))

    def getStateVec(self, state, nodes=None):
        if state not in self.__states:
            raise Exception(str(state) + " has not been added!")
        if nodes is None:
            nodes = self.__nodes
        return map(self.getState, [state]*len(nodes), nodes)

    def getStateStr(self, state, nodes=None):
        if state not in self.__states:
            raise Exception(str(state) + " has not been added!")
        if nodes is None:
            nodes = self.__nodes

        st= myutils.bool2int(self.getStateVec(state, nodes))
        full = bin(st)[2:].rjust(len(nodes), '0')
        return full


    def dcPrint(self):
        stateList = list(self.states)
        stateList.sort()
        stateList = map(lambda x: hex(x), stateList)
        stateList = map(lambda x: x[2:len(x)], stateList)
        idx = range(len(stateList))
        stateStr = map(lambda x,y:"S"+str(x)+"=16#"+str(y), idx, stateList)
        stateStr = reduce(lambda x,y: x + " " + y, stateStr)
        output = str("set_fsm_state_vector {" + 
                     string.join(self.nodes()) + "}\n")
        output += str("set_fsm_encoding {" + stateStr + "}\n")
        return output

    states = property(lambda self: self.__states)

    def nodes(self):
        return self.__nodes

    def __addNumState__(self, state):
        if state >= 2**len(self.__nodes):
            raise Exception("Bad numerical state: " + str(state))
        self.__states.add(state)


    def __addStrState__(self, state):
        num = int(state, 2)
        self.__addNumState__(num)


    def subset(self, nodes):
        return subset(self, nodes)

    def rename(self, conversion):
        return rename(self, conversion)

    def diff(self, state):
        return diff(self, state)

    def init(self):
        return init(self)



def subset(state, nodes):
    "extract a subset of node states"
    for node in nodes:
        if node not in state.nodes():
            raise Exception("node not in state: " + node)

    stateObj = State(nodes)
    for st in state.states:
        vec = state.getStateVec(st, nodes)
        newst = myutils.bool2int(vec)
        stateObj.addState(newst)
    return stateObj
    

def rename(state, conversion):
    "rename nodes in state"
    new = State(map(conversion.get, state.nodes()))
    for st in state.states:
        new.addState(st)
    return new


def diff(state1, state2):
    """ Do a diff, return a new state object """
    if state1.nodes() != state2.nodes():
        raise Exception("Cant diff states with different nodes")

    state  = State(state1.nodes())
    st1 = state1.states
    st2 = state2.states
    diffSt = set.difference(st1, st2)
    if len(diffSt) == 0:
        diffSt = st1
    for st in diffSt:
        state.addState(st)
    return state


def init(state):
    return State(state.nodes())

def merge(state1, state2):
    "merge 2 state instances"
    nodes1 = set(state1.nodes())
    nodes2 = set(state2.nodes())
    nodesCommon = list(set.intersection(nodes1, nodes2))
    nodesCommon.sort()
    nodesCommon.reverse()
    #for node in nodesCommon:
    #    print "merge (info): Node " + node + " is common"

    if len(nodesCommon) > 0:
        # do consistency check!!!
        st1 = subset(state1, nodesCommon)
        st2 = subset(state2, nodesCommon)
        if not st1 == st2:
            #illegal1 = set.difference(st1.states, st2.states)
            #illegal2 = set.difference(st2.states, st1.states)
            #if len(illegal1) > 0 or len(illegal2) > 0:
            raise Exception("Illegal States passed to common merge!!")
        
        # The node ordering is a bit arbitrary but we use this convention:
        # [state1.nodes() + uniqueState2.nodes()]
        nodes2 = list(state2.nodes())
        remove = list()
        for node in nodes2:
            if node in state1.nodes():
                remove.append(node)
        for node in remove:
            nodes2.remove(node)

        allNodes = list(state1.nodes())
        allNodes.extend(nodes2)
        stateObj = State(allNodes)

        for oldState in state1.states:
            for newState in state2.states:
                # only add newState that correspond to oldState
                vec1 = state1.getStateVec(oldState, nodesCommon)
                vec2 = state2.getStateVec(newState, nodesCommon)

                if vec1 == vec2:
                    newStSub = int(state2.getStateStr(newState,nodes2),2)
                    stateObj.addState(oldState* 2**(len(nodes2))+newStSub)

    else:
        if len(state1.states) == 0 and len(state2.states) == 0:
            stateObj = State([])
        elif len(state1.states) == 0:
            stateObj = state2
        elif len(state2.states) == 0:
            stateObj = state1
        else:
            nodes = list(state1.nodes())
            nodes.extend(state2.nodes())
            stateObj = State(nodes)
            for oldState in state1.states:
                for newState in state2.states:
                    stateObj.addState(oldState* 2**(len(state2.nodes()))+newState)

    return stateObj
