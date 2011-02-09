import subprocess
import string
from multiprocessing import Pool
import sys
import time
import hashlib
import os
import re
import pexpect

import pdb

SATexe = "/home/kkelley/Downloads/minisat.mine/simp/minisat_static"

#sat_all = dict()
#sats    = []

def runAll(logic, processes=3, states=None):
    if states is None:
        states = range(2**len(logic.outputs()))
    elif not isinstance(states, list):
        raise Exception("states should be a list!")


    args = zip([logic]*len(states), states)
    solvers = map(SymbolicLogic_solver, args)    


    print "Creating " + str(len(states)) + " CNF files"
    start = time.time()
    cnfargs = zip([logic]*len(states), states, solvers)
    if processes > 1:
        pool = Pool(processes)
        cnffiles = pool.map(SymbolicLogic_cnf, cnfargs)
    else:
        cnffiles = map(SymbolicLogic_cnf, cnfargs)
    dur = time.time() - start
    print "CNF creation took " + str(dur) + " seconds"


    print "Creating " + str(len(states)) + " Assumptions"
    start = time.time()
    if processes > 1:
        pool = Pool(processes)
        assumps = pool.map(SymbolicLogic_assump, args)
    else:
        assumps = map(SymbolicLogic_assump, args)
    dur = time.time() - start
    print "Assumption creation took " + str(dur) + " seconds"


    cnfs = zip(cnffiles, assumps, states, solvers)
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
    # make CNF
    cls = ar[0]
    # ONLY make if the solver doesn't already exist
    if os.path.exists(ar[2]):
        cnffile = None
    else:
        cnffile = cls.cnffile(ar[1], constraints=False)
    return cnffile

def SymbolicLogic_assump(ar, **kwar):
    cls = ar[0]
    assumps = cls.assumptions(ar[1])
    return assumps

def SymbolicLogic_solver(ar, **kwar):
    cls = ar[0]
    solver = "/tmp/solver" + hashlib.sha224(str(cls.outputs()) + str(ar[1])).hexdigest()
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
    

def run(cnf):

    #global sats

    
    # determine solver name
    #m = hashlib.sha224(str(cnf[0])).hexdigest()

    #assumpsFile = "/tmp/assump" + hashlib.sha224(sats[cnf[2]] + str(cnf[1])).hexdigest()
    #f = makeFile(assumpsFile)
    #f.write(cnf[1])
    #f.close()

    if os.path.exists(cnf[3]):
        #print "Solver exists: loading from " + sats[cnf[2]]
        sat = subprocess.Popen([SATexe, "-load", cnf[3], cnf[1]], 
                               stdin=None,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)
    else:
        #print "Loading new solver " + sats[cnf[2]]
        #cnfFile    = "/tmp/cnf" + hashlib.sha224(sats[cnf[2]] + str(cnf[1])).hexdigest()
        #f = makeFile(cnfFile)
        #f.write(cnf[0])
        #f.close()
        sat = subprocess.Popen([SATexe, cnf[0], cnf[1], cnf[3]], 
                               stdin=None,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)
        #os.remove(cnfFile)

    
    #if sats[cnf[2]] is None:
    #    # we must first write cnf[0] and cnf[1] to files
    #    m = hashlib.sha224(str(cnf)).hexdigest()
    #    cnfFile    = "/tmp/inc" + m
    #    #assumpsFile = "/tmp/inc" + m + "1"
    #    f = makeFile(cnfFile)
    #    f.write(cnf[0])
    #    f.close()
    #    #sats[cnf[2]] = pexpect.spawn(SATexe, [cnfFile])
    #    sat = subprocess.Popen([SATexe, cnfFile], 
    #                           stdin=subprocess.PIPE,
    #                           stdout=subprocess.PIPE,
    #                           stderr=subprocess.PIPE)
    #   
    #sat = sats[cnf[2]]

    #f = makeFile(assumpsFile)
    #f.write(cnf[1])
    #f.close()

    #this code was from attempts at sending assumps 1 line at a time
    #result = False
    #for line in string.split(cnf[1], "\n"):
    #    #sat.sendline(line)
    #    #index = sat.expect(["UNSATISFIABLE",
    #    #                    "SATISFIABLE",
    #    #                    pexpect.EOF, 
    #    #                    pexpect.TIMEOUT])
    #    #if index == 1:
    #    #    result = True
    #    #    sats[cnf[2]] = None
    #    #    break
    #    sat.stdin.write(line + "\n")
    #    output = sat.stdout.readline()
    #    output.rstrip()
    #    if output == "SATISFIABLE":
    #        result = True
    #        sat.close()
    #        os.remove(sats[cnf[2]])
    #        break

        
    out = string.split(sat.communicate()[0], "\n")
    #out = string.split(sat.communicate(cnf[0])[0], "\n")

    #pdb.set_trace()

    # parse SAT results here
    #result = out[len(out)-2] != "UNSATISFIABLE"
    result = out[len(out)-2] == "SATISFIABLE"

    # remove files
    # remove assumptions
    os.remove(cnf[1])

    # remove CNF file if it exists
    if cnf[0] and os.path.exists(cnf[0]):
        os.remove(cnf[0])


    # remove serialized solver if it exists
    if result:
        os.remove(cnf[3])




    #try:
    #    cnfFile
    #except NameError:
    #    pass
    #else:
    #    os.remove(cnfFile)


    return result     

