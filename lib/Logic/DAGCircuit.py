from pygraph.classes.digraph import digraph
from pygraph.algorithms.searching import depth_first_search
from pygraph.algorithms.cycles import find_cycle
#import gv
#from pygraph.readwrite.dot import write
import copy

import pdb

class DAGCircuit(digraph):
    "define a DAG circuit"
    def __init__(self, debug=0):
        digraph.__init__(self)

        self.__debug = debug
        self.__inputs  = set()
        self.__outputs = set()
        self.__cells   = set()
        self.__flops   = set()
        self.__virtual = dict() # maps name --> gate
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


    def addInputProtocol(self, protocol):
        """ Connect a virtual FSM to graph inputs """
        
        # first make sure ALL FSM outputs are real module inputs
        # (this should already have been verified but just a sanity check)
        for inp in protocol.outputs().keys():
            if not self.isInput(inp):
                raise Exception("Sanity check failed!")


        # Add node for each virtual gate
        for state in protocol.states().keys():
            self.addCell(state, protocol.states()[state])
            self.__virtual[state] = protocol.states()[state]

        # Each nextstate bit is a large virtual gate
        for state in protocol.nextStates().keys():
            gate = protocol.nextStates()[state]
            self.addCell(gate, gate)
            self.__virtual[gate] = gate

            # connect output to state element
            self.connect(gate, state, gate+"_to_"+state, "out", "D")

            # connect all virtual gate inputs
            self.__connectVirtInputs__(gate, protocol.library())

        # Each output bit is a large virtual gate
        for output in protocol.outputs().keys():
            gate = protocol.outputs()[output]

            # copy all connections
            conns = dict()
            for node in self.node_neighbors[gate]:
                edge = (gate,node)
                conns[edge] = self.__pins[edge]

            # delete existing node
            self.del_node(gate)

            # gate should already be a node, but the problem is that it's
            # a port and it needs to be a cell
            self.addCell(gate, gate)
            self.__virtual[gate] = gate

            # redo all connections on output pin
            for conn in conns.keys():
                cellFrom = conn[0]
                if cellFrom != gate:
                    raise Exception("Something bad happened!")
                cellTo   = conn[1]
                pinFrom  = conns[conn][0]
                for pinTo in conns[conn][1]:
                    if self.__debug > 0:
                        print "Connecting " + str(cellFrom) + " to " + str(cellTo)
                    self.connect(cellFrom, cellTo, cellFrom, "out", pinTo)
            
            # connect all virtual gate inputs
            self.__connectVirtInputs__(gate, protocol.library())
            
    def __connectVirtInputs__(self, gate, library):
        # connect inputs
        for inp in library[gate]['inputs'].keys():
            pinFrom = None
            pinTo   = inp

            # this input is fed back from a design output
            if self.isOutput(inp) or self.isInput(inp) or inp in self.__virtual:
                # todo: connecting an output to an input here *MIGHT*
                # cause a bug ... double-check
                # UPDATE: yep, we need to either create a pass-through 
                # virtual gate for this node, or just remove it completely
                # (1) to remove it, we connect its driving gate (should only
                # be one of these?) to its fanout gate(s), remove it, and
                # ensure we connect it the original pin name to the new gate
                # (2) we can just add a brand new gate to the library
                if self.isOutput(inp):
                    if self.__debug > 0:
                        print str(inp) + " is a feedback output PORT, so it will be removed!"
                    prev = self.node_incidence[inp]
                    if len(prev) != 1:
                        raise Exception("Expected only 1 driver on output")
                    prev = prev[0]
                    pins = self.__pins[(prev, inp)]
                    pinFrom = pins[0]
                    self.del_node(inp)
                    pinTo = inp
                    inp = prev


            # name conflict?!?
            elif inp in self.node_neighbors:
                raise Exception("Name conflict with virtual input " + inp)
            # create a new virtual input
            else:
                if self.__debug > 0:
                    print "Creating VIRTUAL input " + inp + " for " + gate
                self.addPortIn(inp)

            if self.__debug > 0:
                print "Connecting " + str(inp) + " to " + str(gate)

            self.connect(inp, gate, inp, pinFrom, pinTo)
                

    def node2module(self, node):
        if node == "IN_WRITE_CONSUMED":
            pdb.set_trace()
        mod = self.__nl.mods[self.__nl.topMod]
        return self.__virtual[node] if node in self.__virtual else mod.cells[node].submodname

    def breakFlops(self):
        "Traverse the entire graph, break at flop boundaries"

        mod = self.__nl.mods[self.__nl.topMod]
        yaml = self.__nl.yaml

        for node in self.__cells:
            submod = self.node2module(node)
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
   

    def addCell(self, cell, gateName=None):
        mod = self.__nl.mods[self.__nl.topMod]
        yaml = self.__nl.yaml
        self.__cells.add(cell)
        name = gateName if gateName else mod.cells[cell].submodname
        if "clocks" in yaml[name]:
            self.__flops.add(cell)

        digraph.add_node(self,cell)

    def addPortIn(self, port):
        self.__inputs.add(port)
        digraph.add_node(self,port)
        self.connect("__INPUTS__", port, "__dummy__")

    def addPortOut(self, port):
        self.__outputs.add(port)
        digraph.add_node(self,port)
        self.connect(port, "__OUTPUTS__", "__dummy__")

    def removePortOut(self, port):
        if not port in self.__outputs:
            raise exception(port + " is not an output!")
        self.__outputs.remove(port)
        self.del_edge((port, "__OUTPUTS__"))

    def add_node(self, node):
        raise Exception("Cannot call DAGCircuit::add_node directly")

    def add_edge(self, node):
        raise Exception("Cannot call DAGCircuit::add_edge directly")


    def clean(self):
        "Clean the graph; ensure no dangling nodes IN->OUT"
        nodes = dict()
        for node in self.node_neighbors:
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
        if self.__debug > 0:
            print "Removing edge: " + str(edge)
        self.__pins.pop(edge)
        digraph.del_edge(self, edge)


    def del_node(self, node):
        if self.__debug > 0:
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
        if node in self.__virtual:
            self.__virtual.pop(node)
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
        # note: use self._node_neighbors instead of self.nodes() b/c it's fast
        return node in self.node_neighbors and node in self.__cells

    def isInput(self, port):
        return port in self.node_neighbors and port in self.__inputs

    def isOutput(self, port):
        return port in self.node_neighbors and port in self.__outputs

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
        raise Exception("deprecated!")
        #dot = write(self)
        #gvv = gv.readstring(dot)
        #gv.layout(gvv,'dot')
        #gv.render(gvv,'png',fileName)


    cells   = property(lambda self: self.__cells)
    inputs  = property(lambda self: self.__inputs)
    outputs = property(lambda self: self.__outputs)
    flopsIn = property(lambda self: self.__flopsIn)
    flops   = property(lambda self: self.__flops)
