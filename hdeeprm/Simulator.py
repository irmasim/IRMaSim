

from entrypoints.HDeepRMWorkloadManager import HDeepRMWorkloadManager

from manager import JobScheduler, ResourceManager

import heapq

class Simulator:

    def __init__(self, job_limits : dict, jobs : heapq, core_pool: list, platform : dict, options : dict):
        self.job_limits = job_limits
        self.jobs = jobs
        self.core_pool = core_pool
        self.platform = platform
        self.scheduler = HDeepRMWorkloadManager(options)
        self.jobScheduler = JobScheduler()
        self.resourceManager = ResourceManager(platform, core_pool, job_limits)
        self.startSimulation()
        self.time_simulation = 0



    def startSimulation(self):
        first_job = heapq.nsmallest(1, self.jobs)
        #self.scheduler.onJobSubmission(first_job)






