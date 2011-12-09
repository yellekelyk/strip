import ast
import pdb
import string

class Gate2CNF(ast.NodeVisitor):

    def __init__(self, logic):
        self.__logic = logic
        self.__t = ast.parse(logic)

    def getCNF(self, initNames, startNew):
        self.__cnt    = 0
        self.__tmpStart = startNew
        self.__cntNew = self.__tmpStart
        if "out" not in initNames:
            raise Exception("Expected member 'out'")
        self.__initNames = initNames
        self.__names = dict()

        self.__comment = ""
        self.__cnf     = ""
        ast.NodeVisitor.visit(self, self.__t)

        # simple pass-through cases like buffers, flops won't be set yet
        if self.__cnf == "":
            outName = str(initNames.pop('out'))
            if len(initNames) != 1 :
                pdb.set_trace()
                raise Exception("Only expected 1 input!")
            inName = str(initNames.values()[0])
         
            self.__cnf += "-" + inName + " "  + outName + " 0\n"
            self.__cnf +=       inName + " -" + outName + " 0\n"

    def generic_visit(self, node):
        #print type(node).__name__
        ast.NodeVisitor.generic_visit(self, node)

    def visit_Or(self, node):
        #print 'Or: '

        if len(self.__args) < 2:
            raise Exception("Expected at least 2 arguments")

        for i in range(len(self.__args)):
            self.__cnf += "-" + self.__args[i] + " " + self.__name + " 0\n"
        args = string.join(map(str, self.__args), " ")
        self.__cnf +=  args + " -" + self.__name + " 0\n"
        ast.NodeVisitor.generic_visit(self, node)

    def visit_And(self, node):
        #print 'And: '

        if len(self.__args) < 2:
            raise Exception("Expected at least 2 arguments")

        for i in range(len(self.__args)):
            self.__cnf += self.__args[i] + " -" + self.__name + " 0\n"
        args = string.join(map(lambda x:"-"+str(x), self.__args), " ")
        self.__cnf += args + " " + self.__name + " 0\n"
        ast.NodeVisitor.generic_visit(self, node)

    def visit_BoolOp(self, node):
        #print 'BoolOp: op=',node.op, ' values=', node.values, ' cnt=', self.__cnt

        # careful! must call on current node first!
        self.__name = self.getName(node)
        self.__args = map(self.getName, node.values)
        if len(self.__args) < 2:
            pdb.set_trace()
            raise Exception("Expected at least 2 arguments")

        ast.NodeVisitor.generic_visit(self, node)


    def visit_UnaryOp(self, node):
        #print 'UnaryOp: op=',node.op, ' value=', node.operand, ' cnt=', self.__cnt
        # careful! must call on current node first!
        outName = self.getName(node)
        inName  = self.getName(node.operand)

        self.__cnf += "-" + inName + " -" + outName + " 0\n"
        self.__cnf += inName + " " + outName + " 0\n"
        ast.NodeVisitor.generic_visit(self, node)

    def getName(self, node):

        # first check to see if this node has already been named
        if not node in self.__names:
            name = "INITIAL"
            # if this is our first op, use the desired output name
            if self.__cnt == 0:
                self.__names[node] = str(self.__initNames['out'])
                #self.__cnf += self.__names[node] + " 0\n"
                name = 'out'
            # otherwise use the given input name
            elif type(node).__name__ == "Name":
                self.__names[node] = str(self.__initNames[node.id])
                name = node.id
            # or generate an intermed. name
            else:
                self.__names[node] = str(self.__cntNew)
                name = 'tmp'
                self.__cntNew += 1
            self.__cnt += 1
            self.__comment += "c |\t" + self.__names[node] + " = " + name + "\n"

        return self.__names[node]

    cnf    = property(lambda self: self.__cnf)
    comment= property(lambda self: self.__comment)
    tmpvars= property(lambda self: self.__cntNew - self.__tmpStart)


#x = Py2CNF('not(A1 and A2 or not A3))')
#x = Py2CNF('not(A1 and ((A2)))')
#x.getCNF({"A1": 1, "A2": 2, "A3": 3, "out": 3}, 4)

#print x.comment + x.cnf
#print "There were " + str(x.tmpvars) + " tmp vars created"
