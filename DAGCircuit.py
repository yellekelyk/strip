from pygraph.classes.digraph import digraph
from pygraph.algorithms.searching import depth_first_search
from pygraph.algorithms.cycles import find_cycle
import gv
from pygraph.readwrite.dot import write
import copy

class DAGCircuit(digraph):
    "define a DAG circuit"
    def __init__(self):
        digraph.__init__(self)

        self.__inputs  = set()
        self.__outputs = set()
        self.__cells   = set()
        self.__ports   = set()
        self.__pins    = dict()

        # create input, output nodes
        digraph.add_node(self, "__INPUTS__")
        digraph.add_node(self, "__OUTPUTS__")


    def fromNetlist(self, nl, remove=[]):
        self.__nl = nl

        mod = nl.mods[nl.topMod]
        # add a node for all module ports
        for port in mod.ports:
            if port not in remove:
                if mod.ports[port].direction == "in":
                    self.addPortIn(port)
                elif mod.ports[port].direction == "out":
                    self.addPortOut(port)
                else:
                    raise Exception('strange')

        # add a node for each cell (instantiated module // aka gate)
        for cell in mod.cells:
            self.addCell(cell)


        # create edges for all cell pins
        for cell in mod.cells.values():
            for pin in cell.pins.values():
                if pin.port.direction == "in":
                    if pin.net.name not in remove:

                        # "common-case" intramodule driver
                        if pin.net.fanin:
                            self.connect(pin.net.fanin.cell.name, 
                                         cell.name, 
                                         pin.net.name,
                                         pin.net.fanin.name,
                                         pin.name)
                    
                        # some nets might be driven by primary inputs
                        elif pin.net.name in mod.ports:
                            port = mod.ports[pin.net.name]
                            if port.direction == "in":
                                self.connect(port.name,
                                             cell.name, 
                                             pin.net.name,
                                             None,
                                             pin.name)
                            else:
                                raise Exception(str("Bad port direction on port " + 
                                                    port.name))
                        else:
                            raise Exception(str("Pin " + pin.name + " on " + 
                                                cell.name + " is unconnected"))
                
                elif pin.port.direction == "out":
                    for toPin in pin.net.fanout:
                        self.connect(cell.name, 
                                     toPin.cell.name, 
                                     pin.net.name,
                                     pin.name,
                                     toPin.name)

                    if pin.net.name in mod.ports:
                        port = mod.ports[pin.net.name]
                        if port.direction == "out":
                            self.connect(cell.name, 
                                             port.name, 
                                             pin.net.name,
                                             pin.name)
                            
                    elif len(pin.net.fanout) == 0:
                        raise Exception(str("Pin " + pin.name + " on " + 
                                            cell.name + " is unconnected"))

                else:
                    raise Exception("Bad port direction " + pin.port.direction)


    def breakFlops(self):
        "Traverse the entire graph, break at flop boundaries"

        mod = self.__nl.mods[self.__nl.topMod]
        yaml = self.__nl.yaml

        for node in self.__cells:
            submod = mod.cells[node].submodname
            if "clocks" in yaml[submod]:
                # make output port Q a circuit OUTPUT
                # the rationale for this (as opposed to D port) is that
                # some flops have things like Q=D&CIN
                port = yaml[submod]['outputs'].keys()[0]
                wire = self.edge_label((node, self.node_neighbors[node][0]))
                # make a copy of the original children here before modifying
                # the graph
                # be careful! otherwise children is simply a reference!
                children = copy.copy(self.node_neighbors[node])
                self.connect(node, "__OUTPUTS__", wire, port)

                # now create extra dummy input port
                portIn = str(node+"."+port)
                self.addPortIn(portIn)
                for child in children:
                    if self.isCell(child):
                        wire = self.edge_label((node, child))
                        pins = self.__pins[(node,child)]
                        for pin in pins[1]:
                            self.connect(portIn, child, wire, pins[0], pin)

                    # remove the connection between node and child
                    self.del_edge((node,child))

        # remove any dangling nodes!
        self.clean()


        # ensure no cycles (sanity check!)
        cycle = find_cycle(self)
        if len(cycle) > 0:
            raise Exception("Cycle found!: " + str(cycle))

        
    def addInput(self, wire):
        self.__inputs.add(wire)
        self.add_node(wire)
        self.connect("__INPUTS__", wire, "__dummy__")
        
    def addOutput(self, wire):
        self.__outputs.add(wire)
        self.add_node(wire)
        self.connect(wire, "__OUTPUTS__", "__dummy__")

    def addCell(self, cell):
        self.__cells.add(cell)
        digraph.add_node(self,cell)

    def addPortIn(self, port):
        self.__addPort__(port)
        self.connect("__INPUTS__", port, "__dummy__")

    def addPortOut(self, port):
        self.__addPort__(port)
        self.connect(port, "__OUTPUTS__", "__dummy__")

    def __addPort__(self, port):
        self.__ports.add(port)
        digraph.add_node(self,port)


    def add_node(self, node):
        raise Exception("Cannot call DAGCircuit::add_node directly")

    def add_edge(self, node):
        raise Exception("Cannot call DAGCircuit::add_edge directly")


    def clean(self):
        "Clean the graph; ensure no dangling nodes IN->OUT"
        nodes = dict()
        for node in self.nodes():
            nodes[node] = 0

        for node in self.order():
            nodes[node] = 1

        for node in nodes:
            if nodes[node] < 1:
                self.del_node(node)
            

    def del_edge(self, edge):
        print "Removing edge: " + str(edge)
        self.__pins.pop(edge)
        digraph.del_edge(self, edge)


    def del_node(self, node):
        print "Removing node: " + str(node)
        if node in self.__inputs:
            self.__inputs.remove(node)
        if node in self.__outputs:
            self.__outputs.remove(node)
        if node in self.__cells:
            self.__cells.remove(node)
        if node in self.__ports:
            self.__ports.remove(node)
        digraph.del_node(self, node)


    def connect(self, cellFrom, cellTo, wireName, pinFrom=None, pinTo=None):
        edge = ((cellFrom, cellTo))
        
        if edge not in self.edges():
            digraph.add_edge(self, edge)
            self.set_edge_label(edge, wireName)
            self.__pins[edge] = (pinFrom, set())
        else:
            if self.edge_label(edge) != wireName:
                raise Exception(str("Existing edge label is " + 
                                    self.edge_label(edge) + 
                                    " but new label is " + wireName))

        self.__pins[edge][1].add(pinTo)

    def isCell(self, node):
        return node in self.nodes() and node in self.__cells

    def isPort(self, port):
        return port in self.nodes() and port in self.__ports

    def order(self, root='__INPUTS__'):
        st, pre, post = depth_first_search(self, root=root)
        post.reverse()
        return post

    def png(self, fileName):
        dot = write(self)
        gvv = gv.readstring(dot)
        gv.layout(gvv,'dot')
        gv.render(gvv,'png',fileName)
