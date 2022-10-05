import heapq
import math

# TODO Consider removing the entrypoints folder/package
from irmasim.entrypoints.HDeepRMWorkloadManager import HDeepRMWorkloadManager
from irmasim.manager import JobScheduler, ResourceManager
from irmasim.Job import Job
from irmasim.JobQueue import JobQueue
from irmasim.Statistics import Statistics
from irmasim.platform.TaskRunner import TaskRunner
from irmasim.BasicWorkloadManager import BasicWorkloadManager


class Simulator:

    def __init__(self, job_limits: dict, job_queue: JobQueue, core_pool: list, platform: TaskRunner, options: dict):
        self.job_queue = job_queue
        self.platform = platform
        self.scheduler = BasicWorkloadManager(self)
        self.statistics = Statistics(options)
        self.simulation_time = 0
        self.start_simulation()

    def start_simulation(self) -> None:
        first_jobs = self.job_queue.get_next_jobs(self.job_queue.get_next_step())
        self.simulation_time += first_jobs[0].subtime
        self.platform.advance(self.simulation_time)
        # TODO do somenthing with joules
        joules = self.platform.get_joules(self.simulation_time)

        #self.statistics.calculate_energy_and_edp(self.resource_manager.core_pool, self.simulation_time)
        self.scheduler.on_job_submission(first_jobs)

        delta_time_platform = self.platform.get_next_step()
        delta_time_queue = self.job_queue.get_next_step()

        delta_time = min([delta_time_platform, delta_time_queue])

        while delta_time != math.inf:
            if delta_time != 0:
                self.platform.advance(delta_time)
                joules += self.platform.get_joules(delta_time)
                self.simulation_time += delta_time

            if delta_time == delta_time_queue:
                jobs = self.job_queue.get_next_jobs(self.simulation_time)
                self.scheduler.on_job_submission(jobs)

            if delta_time == delta_time_platform:
                jobs = self.job_queue.finish_jobs()
                self.platform.reap([task for job in jobs for task in job.tasks])
                self.scheduler.on_job_completion(jobs)

            delta_time_platform = self.platform.get_next_step()
            delta_time_queue = self.job_queue.get_next_step()

            delta_time = min([delta_time_platform, delta_time_queue])

    def schedule(self, tasks: list):
        self.platform.schedule(tasks)

    def get_next_step(self) -> float:
        return min([self.platform.get_next_step(), self.job_queue.get_next_step()])

    def get_resources(self):
        return self.platform.enumerate_resources()
