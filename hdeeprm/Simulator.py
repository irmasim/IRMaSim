
from entrypoints.HDeepRMWorkloadManager import HDeepRMWorkloadManager

class Simulator:

    def __init__(self, job_limits : dict, jobs : list, core_pool :list, platform : dict, options : dict):
        self.job_limits = job_limits
        self.jobs = jobs
        self.core_pool = core_pool
        self.platform = platform
        #self.scheduler = HDeepRMWorkloadManager(options)
        self.startSimulation()




    def startSimulation(self):
        for i in self.jobs:
            pass


