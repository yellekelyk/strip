import os
import re
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
        self.__queues = 20

        # todo: write script to run multiple SAT per job

    def run(self, jobs):
        outFiles   = dict()
        jobNums    = []
        self.__cnt = 0
             
        # submit all jobs
        jobInfo = []
        for job in jobs:
            jobInfo.append(self.__submit__(job))
        #jobInfo = map(self.__submit__, jobs)
        
        waiting = set(range(self.__cnt))
        jobOuts = [""]*len(jobs)

        # now wait for all jobs to complete
        while len(waiting) > 0:
            jobsWaiting = self.__getJobsWaiting__()

            done = set()

            for idx in waiting:
                jobNum = jobInfo[idx][0]
                jobOut = jobInfo[idx][1]

                # check if the job is finished
                if not jobNum in jobsWaiting:
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
                    jobOuts[idx] = f.read()
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
        outFile = TMPSHARED + "/sge.out." + str(self.__cnt)
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
