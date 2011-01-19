import pdb

class TruthTable:
    "Defines a class for generating truth tables"
    def __init__(self, outputs=[]):
        "outputs should be list of tuples: (inputs, function)"
        self.__inputs = set()
        self.__const  = dict()
        self.__outputs = []

        for output in outputs:
            self.addOutput(output)

    def addOutput(self, output):
        "output is a tuple: (inputs, function)"
        self.__outputs.append(output)
        for outp in output[0]:
            self.__inputs.add(outp)

    def setInput(self, inputName, value):
        if inputName not in self.__inputs and inputName not in self.__const:
            raise Exception("Bad input: " + inputName)
        self.__const[inputName] = value
        if inputName in self.__inputs:
            self.__inputs.remove(inputName)


    def combinations(self):
        return self.__combinations__(len(self.__inputs))

    def __combinations__(self, num):
        if num is 1:
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

    def tblBody(self):
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
            line = self.toLine(combo, outputs)
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
        
