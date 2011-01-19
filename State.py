from odict import OrderedDict

class State:
    "Generic state information for a group of nodes"
    def __init__(self, nodes):
        self.__states = set()
        self.__nodes = OrderedDict()
        cnt = 0
        for node in nodes:
            self.__nodes[node] = cnt
            cnt = cnt + 1

    def addState(self, state):
        if type(state) == type(0):
            self.__addNumState__(state)
        elif type(state) == type(""):
            self.__addStrState__(state)
        else:
            raise TypeError("Bad type received: " + type(state))


    def getState(self, state, node):
        if state not in self.__states:
            raise Exception("state " + str(state) + " not in set of states")
        return bool(int(bin(state)[2:].rjust(len(self.__nodes), '0')[self.__nodes[node]]))
        

    states = property(lambda self: self.__states)
    def nodes(self):
        return self.__nodes.keys()
    #nodes  = property(lambda self: self.__nodes.keys())


    def __addNumState__(self, state):
        if state >= 2**len(self.__nodes):
            raise Exception("Bad numerical state: " + str(state))
        self.__states.add(state)


    def __addStrState__(self, state):
        num = int(state, 2)
        self.__addNumState__(num)

