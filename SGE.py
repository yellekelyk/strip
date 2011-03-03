import math
import os
import re
import stat
import string
import subprocess
import time

import pdb

if "TMPSHARED" in os.environ:
    TMPSHARED = os.environ["TMPSHARED"]
else:
    TMPSHARED="/nobackup/kkelley/tmp"



class SGE:
    def __init__(self):
        self.__asub   = os.environ["SMASH"] + "/bin/asub"
        self.__qstat  = "/sge-root/bin/lx24-amd64/qstat"
        self.__queues = 40


    def writeScript(self, jobs):
        """create a shell-script to run jobs (job, outFile)"""
        fname = TMPSHARED + '/batch' + str(self.__cnt) + '.bash'
        f = open(fname, 'w')
        f.write("#!/bin/bash\n")
        f.write("set -e\n")
        for job in jobs:
            f.write(string.join(job[0], ' ') + ' &> ' + job[1] + '\n')
        f.write("echo Finished!\n")
        f.close()
        os.chmod(fname, stat.S_IREAD | stat.S_IWRITE | stat.S_IEXEC)
        self.__cnt += 1
        return fname
        

    def jobOut(self, num):
        return TMPSHARED + "/sat.out." + str(num)

    def q2Job(self, jobs):
        q = dict()
        for i in range(len(jobs)):
            num = i % self.__queues
            if num not in q:
                q[num] = []
            q[num].append(i)
        return q


    def scripts(self, jobs):
        """ take individual jobs, produces batched scripts """
        self.__cnt = 0

        scripts = []
        #nQueues   = self.__queues
        #if len(jobs) < self.__queues:
        #    nQueues = len(jobs)
        #nJobsPerQ = math.floor(len(jobs)/nQueues)
        #nJobsRmdr = len(jobs) - nQueues * nJobsPerQ
        #jobsCnt = 0
        #for i in range(self.__queues):
        #    jobsInScript = jobs[i*nJobsPerQ:((i+1)*nJobsPerQ)]
        #    if i < nJobsRmdr:
        #        jobsInScript.append(jobs[nJobsPerQ*nQueues+i])
        #
        #    # determine output filenames
        #    outNames = map(self.jobOut, range(jobsCnt, len(jobsInScript)))
        #
        #    jobsCnt += len(jobsInScript)
        #    scripts.append(self.writeScript(zip(jobs, outNames)))
        #return scripts
        q2job = self.q2Job(jobs)        
        for q in q2job:
            jobSubset = []
            for i in q2job[q]:
                jobSubset.append(jobs[i])
            outNames = map(self.jobOut, q2job[q])
            scripts.append(self.writeScript(zip(jobSubset, outNames)))
        return scripts



    def run(self, jobs):
        outFiles   = dict()
        jobNums    = []
             
        # batch jobs into scripts
        scripts = self.scripts(jobs)

        #pdb.set_trace()

        # a dict of q -> job
        q2job = self.q2Job(jobs)  

        # submit all scripts
        self.__cnt = 0
        batchInfo = []
        for job in scripts:
            batchInfo.append(self.__submit__([job]))
        
        waiting = set(range(self.__cnt))
        jobOuts = [""]*len(jobs)

        # now wait for all jobs to complete
        while len(waiting) > 0:
            jobsWaiting = self.__getJobsWaiting__()

            done = set()

            for idx in waiting:
                batchNum = batchInfo[idx][0]
                batchOut = batchInfo[idx][1]

                # check if the batch job is finished
                if not batchNum in jobsWaiting:

                    # now store individual job outputs
                    for job in q2job[idx]:
                        jobOut = self.jobOut(job)
                        # allow some time for the network storage to sync
                        start = time.time()
                        while not os.path.exists(jobOut):
                            # chown should supposedly flush nfs cache
                            os.chown(TMPSHARED, os.geteuid(), -1)
                            dur = time.time() - start
                            if dur > 5:
                                pdb.set_trace()
                                raise Exception(str("Job " + str(jobNum) + 
                                                    " seems to have finished but " + 
                                                    jobOut +  " doesn't exist"))
                    
                        f = open(jobOut)
                        jobOuts[job] = f.read()
                        f.close()
                        os.remove(jobOut)

                    # mark this job as done
                    done.add(idx)

            # remove finished jobs
            for idx in done:
                waiting.remove(idx)

            # sleep before retrying
            if len(waiting) > 0:
                time.sleep(0.3)
                                     
        return jobOuts


    def __submit__(self, job):
        """ Submit a job, return a tuple with (jobNum, outFile) """
        outFile = TMPSHARED + "/batch.out." + str(self.__cnt)
        if os.path.exists(outFile):
            os.remove(outFile)
        self.__cnt += 1
        cmd = [self.__asub, "-o", outFile]
        cmd.extend(job)
        print "submitting " + str(job)
        #pdb.set_trace()
        sge = subprocess.Popen(cmd,
                               stdin=None,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)
        jobNum = string.split(sge.communicate()[0], "\n")
        jobNum = string.split(jobNum[len(jobNum)-3], ".")[0]
        print "num=" + str(jobNum)
        return (jobNum, outFile)
        

    def __getJobsWaiting__(self):
        qstat = subprocess.Popen([self.__qstat],
                                 stdin=None,
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE)
        allJobInfo = string.split(qstat.communicate()[0], "\n")
        allJobInfo.pop(len(allJobInfo)-1)

        jobs = set()
        if len(allJobInfo) > 1:
            # remove the first 2 useless lines
            allJobInfo.pop(0)
            allJobInfo.pop(0)
            for jobInfo in allJobInfo:
                m = re.match("^\s+(\d+)\s+", jobInfo)
                if m:
                    jobs.add(m.group(1))
                else:
                    pdb.set_trace()
                    raise Exception("malformed line " + jobInfo)
        return jobs
