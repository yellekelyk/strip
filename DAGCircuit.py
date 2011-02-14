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
        self.__flops   = set()
        self.__pins    = dict()
        self.__flopsIn = dict()

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
            #print "DAG::fromNetlist processing cell " + cell.name
            for pin in cell.pins.values():
                #print "DAG::fromNetlist processing pin " + pin.name
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
                self.__flopsIn[portIn] = node
                self.addPortIn(portIn)
                self.add_node_attribute(portIn, ('flop',True))
                for child in children:
                    if self.isCell(child):
                        wire = self.edge_label((node, child))
                        pins = self.pins((node,child))
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
   

    def addCell(self, cell):
        mod = self.__nl.mods[self.__nl.topMod]
        yaml = self.__nl.yaml
        self.__cells.add(cell)
        if "clocks" in yaml[mod.cells[cell].submodname]:
            self.__flops.add(cell)

        digraph.add_node(self,cell)

    def addPortIn(self, port):
        self.__inputs.add(port)
        self.__addPort__(port)
        self.connect("__INPUTS__", port, "__dummy__")

    def addPortOut(self, port):
        self.__outputs.add(port)
        self.__addPort__(port)
        self.connect(port, "__OUTPUTS__", "__dummy__")

    def __addPort__(self, port):
        #self.__ports.add(port)
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
            nodes[node] += 1

        for node in self.reverseBFS():
            nodes[node] += 1

        for node in nodes:
            if nodes[node] < 2:
                self.del_node(node)
            elif nodes[node] > 2:
                raise Exception("Touched node " + node + " too many times!")
            

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
        if node in self.__flops:
            self.__flops.remove(node)
        if node in self.__flopsIn:
            self.__flopsIn.pop(node)
        digraph.del_node(self, node)


    def connect(self, cellFrom, cellTo, wireName, pinFrom=None, pinTo=None):
        edge = ((cellFrom, cellTo))
        
        #if edge not in self.edges():
        if not self.has_edge(edge):
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

    def isInput(self, port):
        return port in self.nodes() and port in self.__inputs

    def isOutput(self, port):
        return port in self.nodes() and port in self.__outputs

    def order(self, root='__INPUTS__'):
        st, pre, post = depth_first_search(self, root=root)
        post.reverse()
        return post

    def reverseBFS(self, root='__OUTPUTS__'):
        nodes = [root]
        touched = set()
        while (len(nodes) > 0):
            node = nodes[0]
            nodes = nodes[1:]
            for prev in self.node_incidence[node]:
                if prev not in touched:
                    nodes.append(prev)
                    touched.add(prev)
            yield node

    def pins(self, edge):
        return self.__pins[edge]

    def png(self, fileName):
        dot = write(self)
        gvv = gv.readstring(dot)
        gv.layout(gvv,'dot')
        gv.render(gvv,'png',fileName)


    cells   = property(lambda self: self.__cells)
    inputs  = property(lambda self: self.__inputs)
    outputs = property(lambda self: self.__outputs)
    flopsIn = property(lambda self: self.__flopsIn)
    flops   = property(lambda self: self.__flops)
