import math
import yaml
import FSM

class InputFSMs:
    "Holds / validates many InputFSMs for a design"
    def __init__(self, nl):
        # we need the netlist to validate against
        self.__nl = nl
        self.__fsms = dict()
        self.__inputs = dict()

    def readYAML(self, yamlFile):
        "Read / Parse all FSMs in file"
        file = open(yamlFile)
        fsms = yaml.safe_load(file)
        file.close()

        mod = self.__nl.mods[self.__nl.topMod]

        for fsm in fsms.keys():
            if fsm in self.__fsms:
                raise Exception("Attempt to multiply define " + fsm)
            inputFSM = FSM.FSM(fsms.get(fsm))

            # make sure the outputs make sense
            for out in inputFSM.outputs().keys():
                # make sure it's a port
                if not out in mod.ports:
                    raise Exception("Signal " + out + " isn't a port in " + 
                                    mod.name)
                # make sure it's an input port
                if mod.ports[out].direction != "in":
                    raise Exception("Signal " + out + " is not an INPUT of " + 
                                    mod.name)
                # make sure there is one and only one driver
                if out in self.__inputs:
                    raise Exception("Signal " + out + 
                                    " already has an FSM associated with it")
                # mark this input as being used
                self.__inputs[out] = fsm

            # save the FSM
            self.__fsms[fsm] = inputFSM
            

    def protocols(self):
        return self.__fsms.values()
