from SymbolicLogic import *
from myutils import *
import string
import subprocess

class Logic2CNF(SymbolicLogic):
    def __init__(self, stateProp, flops=[]):
        SymbolicLogic.__init__(self, stateProp, flops)
        self.__l2cnf = "/home/kkelley/Downloads/logic2cnf-0.7.2/logic2cnf"
    
    def fileHeader(self):
        inputs = self.cleanNames(string.join(self.inputs()))
        return "def "  + inputs + ";\n"

    def fileBody(self, state):
        output = applyAnd([self.getOutLogic(state), self.getInLogic()])
        output = self.cleanNames(output)
        output = self.convertOps(output)
        return output + ";\n"

    def cleanNames(self, string):
        string = re.sub("\[", "_", string)
        string = re.sub("\]", "_", string)
        string = re.sub("\.", "_", string)
        string = string.lower()
        return string

    def convertOps(self, string):
        string = re.sub("&",  ".", string)
        string = re.sub("\|", "+", string)
        string = re.sub("!",  "~", string)
        return string

    def cnf(self, state):
        l2cnf = subprocess.Popen([self.__l2cnf, "-c"], 
                                 stdin=subprocess.PIPE, 
                                 stdout=subprocess.PIPE)
        logic = self.fileHeader() + self.fileBody(state)
        #fname = "/tmp/" + str(state) + ".logic"
        #print "Writing Logic File " + fname
        #self.toFile(fname,state)
        return l2cnf.communicate(logic)[0]
        
