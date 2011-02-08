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

sat_all = dict()
sats    = []

def runAll(logic, processes=3, states=None):
    if states is None:
        states = range(2**len(logic.outputs()))
    elif not isinstance(states, list):
        raise Exception("states should be a list!")
        
    #print "Creating CNF files for states=" + str(states)
    print "Creating " + str(len(states)) + " CNF files"

    start = time.time()

    # create all CNFs serially (and cache them in memory)
    #for st in states:
    #    cnf = logic.cnf(st, False)

    # check your lease, you're living in hack city
    #doneCreating = True
    #for st in states:
    #    if not st in logic._Logic2CNF__map:
    #        doneCreating = False
    #        break

    args = zip([logic]*len(states), states)
    cnfs = map(SymbolicLogic_cnf, args)
    #if processes > 1:
    #    pool = Pool(6)
    #    cnfs = pool.map(SymbolicLogic_cnf, args)
    #else:
    #    cnfs = map(SymbolicLogic_cnf, args)




    #
    #if doneCreating or processes == 1:
    #    cnfs = map(SymbolicLogic_cnf, args)
    #else:
    #    pool = Pool(processes)
    #    cnfs = pool.map(SymbolicLogic_cnf, args)
    #    # make sure to save the computed CNFs for next time
    #    for i in range(len(cnfs)):
    #        logic.forceCNF(states[i], cnfs[i][0])
    #        logic.forceMap(states[i], cnfs[i][2])

    dur = time.time() - start
    print "CNF creation took " + str(dur) + " seconds"

    print "Running SAT problems"

    start = time.time()

    if tuple(logic.outputs()) not in sat_all:
        #print "Initializing sat_all for : " + str(logic.outputs())
        sat_all[tuple(logic.outputs())] = [None]*(2**len(logic.outputs()))

    global sats
    sats = sat_all[tuple(logic.outputs())]
    for i in range(len(sats)):
        sats[i] = "/tmp/solver" + hashlib.sha224(str(logic.outputs()) + str(i)).hexdigest()

    #pdb.set_trace()

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
    cnf = cls.cnf(ar[1], constraints=False)

    # get assumption string
    assumps = cls.assumptions(ar[1])

    #inputs = cls.inputs()
    #inputs = map(cls.cleanNames, inputs)
    #mapping = parseCNF(cnf, inputs)


    #fileName = "/tmp/design" + str(ar[1])
    #f = open(fileName + ".cnf", 'w')
    #f.write(cnf)
    #f.close()    
    #
    #f = open(fileName + ".ass", 'w')
    #f.write(assumps)
    #f.close()    
    #
    #print "Wrote " + fileName
    #pair = (cnf, assumps, cls.cnfmap(ar[1]))
    pair = (cnf, assumps, ar[1])
    return pair

    
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
    
    # determine solver name
    #m = hashlib.sha224(str(cnf[0])).hexdigest()

    assumpsFile = "/tmp/assump" + hashlib.sha224(sats[cnf[2]] + str(cnf[1])).hexdigest()
    f = makeFile(assumpsFile)
    f.write(cnf[1])
    f.close()

    global sats
    if os.path.exists(sats[cnf[2]]):
        #print "Solver exists: loading from " + sats[cnf[2]]
        sat = subprocess.Popen([SATexe, "-load", sats[cnf[2]], assumpsFile], 
                               stdin=None,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)
    else:
        #print "Loading new solver " + sats[cnf[2]]
        #m = hashlib.sha224(str(cnf)).hexdigest()
        cnfFile    = "/tmp/cnf" + hashlib.sha224(sats[cnf[2]] + str(cnf[1])).hexdigest()
        f = makeFile(cnfFile)
        f.write(cnf[0])
        f.close()
        sat = subprocess.Popen([SATexe, cnfFile, assumpsFile, sats[cnf[2]]], 
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
    #os.remove(cnfFile)
    os.remove(assumpsFile)
    if result:
        os.remove(sats[cnf[2]])


    try:
        cnfFile
    except NameError:
        pass
    else:
        os.remove(cnfFile)


    return result     

