import State
import pdb 


#from State import *

#class StateSuperSet(State):
# note - probably don't want to actually derive from State
class StateSuperset:
    """ This class mimics a State class, but in reality has many (possibly overlapping) State classes under the hood """
    def __init__(self, states):
        self.__states = states
        
        # find superset of nodes
        nodeSet = set()
        for state in states:
            for node in state.nodes():
                nodeSet.add(node)
        nodeList = list(nodeSet)
        nodeList.sort()
        nodeList.reverse()
        self.__nodes = nodeList


    def __eq__(self, state):
        return state.subgroups() == self.__states

    def __ne__(self, state):
        return not self.__eq__(state)

    def full(self):
        ret = True
        for state in self.__states:
            ret = ret and state.full()
        return ret

    def subgroups(self):
        return self.__states

    def dcPrint(self):
        ret = ''
        for state in self.__states:
            if not state.full():
                ret += state.dcPrint()
        return ret

    def annotation(self, num):
        merge = State.State([])
        for state in self.__states:
            if not state.full():
                merge = State.merge(merge, state)
        return merge.annotation(num)


    def nodes(self):
        return self.__nodes

    def numAllStates(self):
        ret = 0
        for state in self.__states:
            ret += state.numAllStates()
        return ret

    def numStates(self):
        ret = 0
        for state in self.__states:
            ret += state.numStates()
        return ret


    def update(self, newState):
        #idxs = set()
        #for node in state.nodes():
        #    if node not in self.__nodes:
        #        raise Exception("missing node " + node)
        #    idxs.add(self.__nodes.index(node))
        #
        ## for each underlying state object, update with subset
        #for idx in idxs:
        for state in self.__states:
            newSt = State.subset(newState, state.nodes())
            for st in newSt.states:
                state.addState(st)
            

    def subset(self, nodes):
        return subset(self, nodes)

    def rename(self, conversion):
        return rename(self, conversion)

    def diff(self, sss):
        return diff(self, sss)

    def init(self):
        return init(self)

    


def subset(sss, nodes):
    newStates = []
    for state in sss.subgroups():
        nodesCommon = []
        for node in nodes:
            if node in state.nodes():
                nodesCommon.append(node)
        if len(nodesCommon) > 0:
            newStates.append(state.subset(nodesCommon))
    return StateSuperset(newStates)


def rename(sss, conversion):
    newStates = []
    for state in sss.subgroups():
        newStates.append(state.rename(conversion))
    return StateSuperset(newStates)


def diff(sss1, sss2):
    """ Do a diff, return a new StateSuperset object """
    if sss1.nodes() != sss2.nodes():
        raise Exception("Cannot diff different nodes")
        
    if len(sss1.subgroups()) != len(sss2.subgroups()):
        pdb.set_trace()
        raise Exception("Cannot diff different subgroups")

    states = []
    sub1 = sss1.subgroups()
    sub2 = sss2.subgroups()
    for i in range(len(sub1)):
        states.append(sub1[i].diff(sub2[i]))

    return StateSuperset(states)



def init(sss):
    """ Initialize a new sss using the same states/nodes """
    states = []
    for state in sss.subgroups():
        states.append(state.init())
    return StateSuperset(states)
