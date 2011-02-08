import subprocess
import string
from multiprocessing import Pool
import sys
import time

import pdb

SATexe = "/home/kkelley/Downloads/minisat/core/minisat_static"

def runAll(logic, processes=3, states=None):
    if states is None:
        states = range(2**len(logic.outputs()))
    elif not isinstance(states, list):
        raise Exception("states should be a list!")
        
    #print "Creating CNF files for states=" + str(states)
    print "Creating " + str(len(states)) + " CNF files"

    args = zip([logic]*len(states), states)
    #print "args=" + str(args)

    start = time.time()
    if processes > 1:
        pool = Pool(6)
        cnfs = pool.map(SymbolicLogic_cnf, args)
    else:
        cnfs = map(SymbolicLogic_cnf, args)

    dur = time.time() - start
    print "CNF creation took " + str(dur) + " seconds"
    print "Running SAT problems"
    start = time.time()
    if processes > 1:
        pool = Pool(processes)
        results = pool.map(run, cnfs)
    else:
        results = map(run, cnfs)
    dur = time.time() - start
    print "SAT runs took " + str(dur) + " seconds"
    
    # convert binary array to set
    outSet = set()
    for idx in range(len(results)):
        if results[idx]:
            outSet.add(states[idx])
    return outSet

def SymbolicLogic_cnf(ar, **kwar):
    cls = ar[0]
    cnf = cls.cnf(ar[1])
    #print "CNF created for " + str(ar[1])
    return cnf

    
def run(cnf):
    sat = subprocess.Popen([SATexe], 
                           stdin=subprocess.PIPE, 
                           stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE)
    out = string.split(sat.communicate(cnf)[0], "\n")
    result = out[len(out)-2] != "UNSATISFIABLE"
    return result     

