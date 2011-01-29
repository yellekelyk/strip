import myutils
import re
import pdb

class TruthTable:
    "Defines a class for generating truth tables"
    def __init__(self, stateProp, flops=[]):
        self.__inputs = set()
        self.__const  = dict()
        self.__outputs = []
        self.__stateProp = stateProp

        if len(flops) == 0:
            flops = stateProp.defaultFlops()

        # create anonymous functions for simulating
        for flop in flops:
            inps = list(stateProp.deps[flop])
            #inps = list(stateProp.deps[flop].difference(stateProp.state.nodes()))
            ## ** MUST make clean lambda function input names!!!!
            evalStr = "lambda "
            evalStr += reduce(lambda x,y: x + ',' + y, inps)
            evalStr += ": " + stateProp.sim[flop]
            # before evaluating, do regex replacing of input names
            for i in range(0, len(inps)):
                inp = re.sub("\[", "\\[", inps[i])
                inp = re.sub("\]", "\\]", inp)
                inp = re.sub("\.", "\\.", inp)
                evalStr = re.sub(inp, str("in"+str(i)), evalStr)
            func = eval(evalStr)
            self.addOutput((inps, func))


    def addOutput(self, output):
        "output is a tuple: (inputs, function)"
        self.__outputs.append(output)
        for outp in output[0]:
            self.__inputs.add(outp)

    def setInput(self, inputName, value):
        if inputName not in self.__inputs and inputName not in self.__const:
            print "Warning: Input " + inputName + " isn't used"
            #raise Exception("Bad input: " + inputName)
        else:
            self.__const[inputName] = value
            if inputName in self.__inputs:
                self.__inputs.remove(inputName)


    def combinations(self):
        return self.__combinations__(len(self.__inputs))

    def __combinations__(self, num):
        #print "combinations: " + str(num)
        if num is 0:
            yield []
        elif num is 1:
            yield [True]
            yield [False]
        else:
            for i in self.__combinations__(num-1):
                yield i + [True]
                yield i + [False]


    def toString(self, debug=False):
        string = self.tblHeader()
        for line in self.tblBody():
            string += line
        string += self.tblFooter()
        return string

    def eval(self):
        for combo in self.combinations():
            inputs = dict(zip(self.__inputs,combo))
            inputs.update(self.__const)
            outputs = []
            # evaluate outputs
            for output in self.__outputs:
                # construct arguments in order
                argList = []
                #pdb.set_trace()
                for arg in output[0]:
                    argList.append(inputs[arg])
                outputs.append(output[1](*argList))
            yield (combo, outputs)

    def tblBody(self):
        for result in self.eval():
            line = self.toLine(result[0], result[1])
            yield str(line + "\n")

    def tblHeader(self):
        string  = ".i " + str(len(self.__inputs)) + "\n"
        string += ".o " + str(len(self.__outputs)) + "\n"
        return string

    def tblFooter(self):
        string  = ".e\n"
        return string

    def toLine(self, combo, outputs):
        #pdb.set_trace()
        string = self.arrToString(self.__const.values())
        string += self.arrToString(combo) + " "
        string += self.arrToString(outputs)
        return string

    def arrToString(self, arr):
        string = str()
        for val in arr:
            string = string + str(int(val))
        return string
        

    def toFile(self, fileName):
        state = self.__stateProp.state
        f = open(fileName, 'w')
        f.write(self.tblHeader())
        for state in state.states:
            for node in state.nodes():
                val = state.getState(state, node)
                self.setInput(node, val)
            for line in self.tblBody():
                f.write(line)

        f.write(tt.tblFooter())
        f.close()


    def sweepStates(self):
        states = set()
        state = self.__stateProp.state
        for st in state.states:
            for node in state.nodes():
                val = state.getState(st, node)
                self.setInput(node, val)
            for combo,outputs in self.eval():
                states.add(myutils.bool2int(outputs))
        return states
