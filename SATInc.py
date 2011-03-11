import subprocess
import string
from multiprocessing import Pool
import sys
import time
import hashlib
import os
import re
import SGE

import pdb

if "MINISAT" in os.environ:
    MINISAT = os.environ["MINISAT"]
else:
    MINISAT = "/home/kkelley/Downloads/minisat.mine/simp/minisat_static"

if "TMPDIR" in os.environ:
    TMPDIR = os.environ["TMPDIR"]
else:
    TMPDIR="/tmp"


def runAll(logic, processes=1, states=None):
    if states is None:
        states = range(2**len(logic.outputs()))
    elif not isinstance(states, list):
        raise Exception("states should be a list!")

    print "Creating CNF File"
    start = time.time()
    cnffile = logic.cnffile()
    dur = time.time() - start
    print "CNF creation took " + str(dur) + " seconds"


    print "Creating Input Assumption Files"
    start = time.time()
    assumpsIn = logic.assumptionsIn()
    dur = time.time() - start
    print "Input Assumption creation took " + str(dur) + " seconds"


    print "Creating Output Assumption Files"
    start = time.time()
    (assumpsOut, stateGroups) = logic.assumptionsOutGroup(states, processes)
    dur = time.time() - start
    print "Output Assumption creation took " + str(dur) + " seconds"

    runArgs = zip([cnffile]*len(assumpsOut), 
                  [assumpsIn]*len(assumpsOut), 
                  assumpsOut, 
                  stateGroups)
    

    print "Sweeping " + str(len(states)) + " SAT problems"
    start = time.time()
    if len(assumpsOut) > 1:
        pool = Pool(len(assumpsOut))
        resultstmp = pool.map(run, runArgs)
        results = []
        for result in resultstmp:
            results.extend(result)
    else:
        results = run(runArgs[0])


    dur = time.time() - start
    print "SAT runs took " + str(dur) + " seconds"

    # remove assumption files here
    for assump in assumpsIn:
        os.remove(assump)
    for assump in assumpsOut:
        os.remove(assump)   

    # convert binary array to set
    outSet = set()
    for idx in range(len(results)):
        if results[idx]:
            outSet.add(states[idx])
    return outSet
         

def getResults(output, n=1):
    out    = string.split(output, "\n")
    filtered = out[len(out)-1-n:len(out)-1]
    return map(lambda x:x == "SATISFIABLE", filtered)


def makeSATArgs(arr):
    satArgs = [MINISAT, "-cnf="+str(arr[0]), "-output="+str(arr[2])]
    satArgs.extend(arr[1])
    return satArgs


def run(cnf):
    satArgs = makeSATArgs(cnf)
    sat = subprocess.Popen(satArgs,
                           stdin=None,
                           stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE)
        
    result = getResults(sat.communicate()[0], len(cnf[3]))

    return result     


def runSGE(cnfs):
    jobs = map(makeSATArgs, cnfs)
    sge = SGE.SGE()
    outputs = sge.run(jobs)
    return map(getResults, outputs)
