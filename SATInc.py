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


    args = zip([logic]*len(states), states)
    solvers = map(SymbolicLogic_solver, args)    
    solvers = [solvers[0]]*len(states)

    # todo: we could try creating 1 cnf file and len(states) assumption files
    # this will allow us to get away with 1 solver instance
    # (but probably won't change the SAT solve times very much 
    # but it will save on disk space / bandwidth with 1 solver file instead
    print "Creating " + str(len(states)) + " CNF files"
    start = time.time()
    cnfargs = zip([logic]*len(states), states, solvers)
    #if cnfprocesses > 1:
    #    pool = Pool(cnfprocesses)
    #    cnffiles = pool.map(SymbolicLogic_cnf, cnfargs)
    #else:
    #    cnffiles = map(SymbolicLogic_cnf, cnfargs)
    cnffile  = SymbolicLogic_cnf(cnfargs[0])
    cnffiles = [cnffile]*len(cnfargs)
    dur = time.time() - start
    print "CNF creation took " + str(dur) + " seconds"


    #pdb.set_trace()

    # the assumptions (input constraints) are actually the same across outputs
    # this implies we can get away with 1 assumption file PER group
    print "Creating Input Assumption Files"
    start = time.time()
    assumpsIn = logic.assumptionsIn()
    dur = time.time() - start
    print "Input Assumption creation took " + str(dur) + " seconds"

    print "Creating Output Assumption Files"
    start = time.time()
    #assumpsOut = logic.assumptionsOut(states)
    assumpsOut = logic.assumptionsOutAll(states)
    dur = time.time() - start
    print "Output Assumption creation took " + str(dur) + " seconds"


    #if not os.path.exists(solvers[0]):
    #    print "Creating Solver"
    #    start = time.time()
    #    #satArgs = [MINISAT, "-cnf="+cnffile]
    #    satArgs = [MINISAT, "-cnf="+cnffile, "-output="+assumpsOut[0]]
    #    satArgs.extend(assumpsIn)
    #    satArgs.append("-save="+solvers[0])
    #    sat = subprocess.Popen(satArgs,
    #                           stdin=None,
    #                           stdout=subprocess.PIPE,
    #                           stderr=subprocess.PIPE)
    #    sat.communicate()
    #    dur = time.time() - start
    #    print "Solver Creation took " + str(dur) + " seconds"


    #pdb.set_trace()

    cnfs = zip(cnffiles, [assumpsIn]*len(cnffiles), assumpsOut, states, solvers)
    print "Running SAT problems"
    start = time.time()
    if processes > 1:
        # use solver creation time to estimate total runtime
        # this time estimated from CC numbers on neva-2
        #timeEst = dur * len(cnfs) / (processes/2)
        timeEst = (dur*len(cnfs) * 0.31 + 2.24)/2
        print "Estimated SAT solve time: " + str(timeEst)
        timeEst = 0
        if timeEst > 20:
            print "Running on grid..."
            results = runSGE(cnfs)
        else:
            pool = Pool(processes)
            results = pool.map(run, cnfs)
    else:
        #results = map(run, cnfs)
        results = run((cnffile, assumpsIn, assumpsOut, states, solvers[0]))
    dur = time.time() - start
    print "SAT runs took " + str(dur) + " seconds"

    #pdb.set_trace()

    # remove assumption files here
    for assump in assumpsIn:
        os.remove(assump)
    os.remove(assumpsOut)
    #for assump in assumpsOut:
    #    os.remove(assump)   
    #if cnffile and os.path.exists(cnffile):
    #    os.remove(cnffile)
    #os.remove(solvers[0])

    # convert binary array to set
    outSet = set()
    for idx in range(len(results)):
        if results[idx]:
            outSet.add(states[idx])
    return outSet
         

def SymbolicLogic_cnf(ar, **kwar):
    # make CNF
    cls = ar[0]
    # ONLY make if the solver doesn't already exist
    if os.path.exists(ar[2]):
        cnffile = None
    else:
        #cnffile = cls.cnffile(ar[1], constraints=False)
        #cnffile = cls.cnffile(0, constraints=False)
        cnffile = cls.cnffile()
    return cnffile

def SymbolicLogic_assump(ar, **kwar):
    cls = ar[0]
    assumps = cls.assumptions(ar[1])
    return assumps

def SymbolicLogic_solver(ar, **kwar):
    cls = ar[0]
    solver = TMPDIR + "/solver" + hashlib.sha224(str(cls.outputs()) + str(ar[1])).hexdigest()
    return solver

    
def makeFile(fname):
    # use the try/except to check for collisions
    #try:
    newfd = os.open(fname, os.O_EXCL | os.O_CREAT | os.O_RDWR)
    new_file = os.fdopen(newfd, 'w')
    #except OSError, x:
    #    if x[1] == 'File exists':
    #        raise Exception(fname + " exists!")

    return new_file
    

def getResults(output, n=1):
    out    = string.split(output, "\n")
    filtered = out[len(out)-1-n:len(out)-1]
    #pdb.set_trace()
    #return out[len(out)-2] == "SATISFIABLE"
    return map(lambda x:x == "SATISFIABLE", filtered)


def makeSATArgs(arr):
    #satArgs = [MINISAT, "-load="+str(arr[4]), "-output="+str(arr[2])]
    satArgs = [MINISAT, "-cnf="+str(arr[0]), "-output="+str(arr[2])]
    satArgs.extend(arr[1])
    return satArgs


def run(cnf):

    #if cnf[3] == 18:
        #pdb.set_trace()

    #if os.path.exists(cnf[4]):
    satArgs = makeSATArgs(cnf)
    sat = subprocess.Popen(satArgs,
                           stdin=None,
                           stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE)
    #else:
    #    raise Exception("Solver doesn't exist")
        
    result = getResults(sat.communicate()[0], len(cnf[3]))

    return result     


def runSGE(cnfs):
    jobs = map(makeSATArgs, cnfs)
    sge = SGE.SGE()
    outputs = sge.run(jobs)
    return map(getResults, outputs)
