import subprocess
import string
from multiprocessing import Pool
import sys
import time

SATexe = "/home/kkelley/Downloads/minisat/core/minisat_static"

def runAll(logic, processes=4):
    print "Creating CNF files"
    nruns = 2**len(logic.outputs())
    args = zip([logic]*nruns, range(nruns))

    start = time.time()
    if processes > 1:
        pool = Pool(processes)
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
    return results


def SymbolicLogic_cnf(ar, **kwar):
    cls = ar[0]
    return cls.cnf(ar[1])

    
def run(cnf):
    sat = subprocess.Popen([SATexe], 
                           stdin=subprocess.PIPE, 
                           stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE)
    out = string.split(sat.communicate(cnf)[0], "\n")
    result = out[len(out)-2] != "UNSATISFIABLE"
    return result     

