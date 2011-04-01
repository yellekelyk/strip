import pdb

class DC:
    def __init__(self, sg):
        keys = sg.keys()
        keys.sort()
        self.__prev = None
        for key in keys:
            st = sg.get(key)
            if not st.full():
                #print self.__pre__(key)
                print st.dcPrint()
                #print self.__post__(key)
                self.__prev = key


    def __pre__(self, key):
        ret = str()
        if self.__prev == None:
            pass
        else:
            ret += "remove_design\n"
            #ret += "read_verilog ${TMP_DIR}/${DESIGN_NAME}." + str(self.__prev) + ".v\n"
            ret += "read_verilog ${PREV_DESIGN}\n"

        ret += "source ${COMMON_DIR}/clock.tcl\n"
        ret += "source ${COMMON_DIR}/flatten.tcl\n"
        ret += "set fsm_auto_inferring 0\n"
        ret += "set fsm_enable_state_minimization 1\n"
        ret += "set_fsm_minimize true\n"
        return ret

    def __post__(self, key):
        ret = str()
        ret += "compile_ultra\n"
        areaFile = "${LOG_DIR}/area.fsm." + str(key) + ".rpt"
        verilogFile = "${TMP_DIR}/${DESIGN_NAME}." + str(key) + ".v"
        ret += "report_area > " + areaFile + "\n"
        ret += "report_timing > ${LOG_DIR}/timing.fsm." + str(key) + ".rpt\n"
        ret += "report_fsm > ${LOG_DIR}/fsm." + str(key) + ".rpt\n"
        ret += "write -format verilog -output " + verilogFile + "\n"
        ret += "set area [exec /home/kkelley/bin/area.bash " + areaFile + "]\n"
        ret += "set best [expr $area < $area_best]\n"
        ret += "if ($best) {\n"
        ret += "  set area_best $area\n"
        ret += "  set PREV_DESIGN " + verilogFile + "\n"
        ret += "}\n"
        ret += "echo $area_best\n"
        return ret
