from pygraph.classes.digraph import digraph
from pygraph.algorithms.searching import depth_first_search
from pygraph.algorithms.searching import breadth_first_search
import gv
from pygraph.readwrite.dot import write
import copy

class GateGraph(digraph):
    "turns a Verilog gate-level netlist into a digraph"
    def __init__(self, nl, remove=[]):
        digraph.__init__(self)

        mod = nl.mods[nl.topMod]

        self.__pins = dict()

        self.add_node("__INPUTS__")
        self.add_node_attribute("__INPUTS__", ("dummy", True))
        self.add_node("__OUTPUTS__")
        self.add_node_attribute("__OUTPUTS__", ("dummy", True))

        # add a node for all module ports
        for port in mod.ports:
            if port not in remove:
                self.add_node(port)
                self.add_node_attribute(port, ("port", True))

        # add a node for each cell (instantiated module // aka gate)
        for cell in mod.cells:
            self.add_node(cell)
            self.add_node_attribute(cell, ("cell", True))

        # create edges for all cell pins
        for cell in mod.cells.values():
            for pin in cell.pins.values():
                if pin.port.direction == "in":
                    if pin.net.name not in remove:

                    # "common-case" intramodule driver
                        if pin.net.fanin:
                            self.__addEdge__(pin.net.fanin.cell.name, 
                                             cell.name, 
                                             pin.net.name,
                                             pin.net.fanin.name,
                                             pin.name)
                    
                    # some nets might be driven by primary inputs
                        elif pin.net.name in mod.ports:
                            port = mod.ports[pin.net.name]
                            if port.direction == "in":
                                self.__addEdge__("__INPUTS__",
                                                 port.name,
                                                 "__dummy__")

                                self.__addEdge__(port.name,
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
                        self.__addEdge__(cell.name, 
                                         toPin.cell.name, 
                                         pin.net.name,
                                         pin.name,
                                         toPin.name)

                    if pin.net.name in mod.ports:
                        port = mod.ports[pin.net.name]
                        if port.direction == "out":
                            self.__addEdge__(cell.name, 
                                             port.name, 
                                             pin.net.name,
                                             pin.name)
                            self.__addEdge__(port.name, 
                                             "__OUTPUTS__", 
                                             "__dummy__")
                            
                    elif len(pin.net.fanout) == 0:
                        raise Exception(str("Pin " + pin.name + " on " + 
                                            cell.name + " is unconnected"))

                else:
                    raise Exception("Bad port direction " + pin.port.direction)



    def order(self, root='__INPUTS__'):
        st, pre, post = depth_first_search(self, root=root)
        post.reverse()
        return post

    def bfs(self, root='__INPUTS__'):
        st, nodes = breadth_first_search(self, root=root)
        return nodes

    def png(self, fileName):
        dot = write(self)
        gvv = gv.readstring(dot)
        gv.layout(gvv,'dot')
        gv.render(gvv,'png',fileName)
        
    def subgraph(self, nodes):
        g = copy.deepcopy(self)
        for node in g.order():
            if node not in nodes:
                g.del_node(node)
        return g

    def pins(self, edge):
        return self.__pins[edge]

    def iscell(self, node):
        return ('cell', True) in self.node_attributes(node)

    def isport(self, node):
        return ('port', True) in self.node_attributes(node)

    def del_edge(self, edge):
        self.__pins.pop(edge)
        digraph.del_edge(self, edge)

    def __addEdge__(self, cellFrom, cellTo, wireName, pinFrom=None, pinTo=None):
        edge = ((cellFrom, cellTo))
        
        #print "considering edge " + cellFrom + "-->" + cellTo

        if edge not in self.edges():
            #print "adding edge " + cellFrom + "-->" + cellTo
            self.add_edge(edge)
            self.set_edge_label(edge, wireName)
            self.__pins[edge] = (pinFrom, set())
            #self.__pins[edge] = (pinFrom, pinTo)
        else:
            if self.edge_label(edge) != wireName:
                raise Exception(str("Existing edge label is " + 
                                    self.edge_label(edge) + 
                                    " but new label is " + wireName))

        self.__pins[edge][1].add(pinTo)

