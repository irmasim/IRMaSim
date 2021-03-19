from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from entrypoints.HDeepRMWorkloadManager import HDeepRMWorkloadManager

from manager import JobScheduler, ResourceManager
from Job import Job

import heapq


class Simulator:

    def __init__(self, job_limits: dict, jobs_queue: heapq, core_pool: list, platform: dict, options: dict):
        self.job_limits = job_limits
        self.core_pool = core_pool
        self.platform = platform
        self.scheduler = HDeepRMWorkloadManager(options, self)
        self.job_scheduler = JobScheduler(jobs_queue)
        self.resource_manager = ResourceManager(platform, core_pool, job_limits)
        self.simulation_time = 0
        self.start_simulation()

    def start_simulation(self):
        first_job = self.job_scheduler.pop_first_job_in_queue()
        self.simulation_time = first_job.subtime
        first_job.time_left = first_job.req_time
        self.scheduler.onJobSubmission(first_job)
        self.start_static_jobs()

    def start_static_jobs(self):

        while self.job_scheduler.nb_jobs_queue_left > 0:

            self.peek_jobs_now()
            self.finish_jobs_now()
            self.scheduler.onNoMoreEvents()

            

        self.complete_all_jobs()

    def finish_jobs_now(self):
        finish_jobs = self.job_scheduler.finish_jobs_now()
        for i in finish_jobs:
            self.scheduler.onJobCompletion(i)
            self.resource_manager.update_state(i, [x.id for x in i.cores], 'FREE', self.simulation_time)

    def peek_jobs_now(self):
        while self.job_scheduler.nb_jobs_queue_left > 0 and \
                self.job_scheduler.show_first_job_in_queue().subtime == self.simulation_time:
            job = self.job_scheduler.pop_first_job_in_queue()
            self.scheduler.onJobSubmission(job)
            self.job_scheduler.new_job(job)

    def complete_all_jobs(self):
        self.end_simulation()

    def end_simulation(self):
        self.scheduler.onSimulationEnds()

    def nb_pending_jobs(self) -> int:
        return self.job_scheduler.nb_pending_jobs