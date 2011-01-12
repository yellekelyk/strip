
class State:
    "Generic state information for semi-lattice analysis"
    def __init__(self):
        pass


class Top(State):
    def __init__(self):
        State.__init__(self)


class Bottom(State):
    def __init__(self):
        State.__init__(self)

