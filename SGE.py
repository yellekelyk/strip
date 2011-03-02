import subprocess
import os
import string

if "TMPDIR" in os.environ:
    TMPDIR = os.environ["TMPDIR"]
else:
    TMPDIR="/tmp"


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
        waiting = range(self.__cnt)
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
                    else:
                        raise Exception(str("Job " + str(jobNum) + 
                                            " seems to have finished but " + 
                                            jobOut +  " doesn't exist"))
                    
                    # mark this job as done
                    done.add(idx)

            # remove finished jobs
            for idx in done:
                waiting.pop(idx)
                                     
        return jobOuts


    def __submit__(self, job):
        """ Submit a job, return a tuple with (jobNum, outFile) """
        outFile = TMPDIR + "/sge.out." + str(self.__cnt)
        self.__cnt += 1
        sge = subprocess.Popen([self.__asub, "-o", outFile, job],
                               stdin=None,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)
        jobNum = string.split(sge.communicate()[0], "\n")
        jobNum = string.split(jobNum[len(jobNum)-1], ".")[0]
        return (jobNum, outFile)
        

    def __getJobsWaiting__(self):
        qstat = subprocess.Popen([self.__qstat]
                                 stdin=None,
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE)
        allJobInfo = string.split(qstat.communicate()[0], "\n")
        jobs = set()
        if len(allJobInfo > 0):
            # remove the first 2 useless lines
            allJobInfo.pop(0)
            allJobInfo.pop(0)
            for jobInfo in allJobInfo:
                m = re.match("^\s+(\d+)\s+", jobInfo)
                if m:
                    jobs.add(m.group(1))
                else:
                    raise Exception("malformed line " + jobInfo)
        return jobs
