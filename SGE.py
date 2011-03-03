import os
import re
import string
import subprocess
import time

import pdb

if "TMPDIR" in os.environ:
    TMPDIR = os.environ["TMPDIR"]
else:
    TMPDIR="/tmp"

TMPDIR="/nobackup/kkelley/tmp"


class SGE:
    def __init__(self):
        self.__asub  = os.environ["SMASH"] + "/bin/asub"
        self.__qstat = "/sge-root/bin/lx24-amd64/qstat"

    def map(self, jobs):
        outFiles   = dict()
        jobNums    = []
        self.__cnt = 0
             
        # submit all jobs
        jobInfo = map(self.__submit__, jobs)
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
                    # check if the output file exists
                    if os.path.exists(jobOut):
                        f = open(jobOut)
                        jobOuts[idx] = f.read()
                        f.close()
                        os.remove(jobOut)
                    else:
                        raise Exception(str("Job " + str(jobNum) + 
                                            " seems to have finished but " + 
                                            jobOut +  " doesn't exist"))
                    
                    # mark this job as done
                    done.add(idx)

            # remove finished jobs
            for idx in done:
                waiting.remove(idx)

            # sleep before retrying
            if len(waiting) > 0:
                time.sleep(0.5)
                                     
        return jobOuts


    def __submit__(self, job):
        """ Submit a job, return a tuple with (jobNum, outFile) """
        outFile = TMPDIR + "/sge.out." + str(self.__cnt)
        if os.path.exists(outFile):
            os.remove(outFile)
        self.__cnt += 1
        cmd = [self.__asub, "-o", outFile]
        cmd.extend(job)
        sge = subprocess.Popen(cmd,
                               stdin=None,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)
        jobNum = string.split(sge.communicate()[0], "\n")
        jobNum = string.split(jobNum[len(jobNum)-3], ".")[0]
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
