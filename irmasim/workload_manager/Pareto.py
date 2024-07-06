from irmasim.workload_manager.Minimal import Minimal
from irmasim.Job import Job
from irmasim.Task import Task
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from irmasim.Simulator import Simulator

class Pareto(Minimal):
    def __init__(self, simulator: 'Simulator'):
        super(Pareto, self).__init__(simulator)
        if simulator.platform.config["model"] != "modelV1":
            raise Exception("Pareto workload manager needs a modelV1 platform")
        self.resources = [ [ resource_id, 1 ] for resource_id in self.simulator.get_resources_ids() ]
        self.idle_resources = len(self.resources)
        self.pending_jobs = []
        self.running_jobs = []

    def on_job_submission(self, jobs: list):
        print("Pareto on_job_submission")
        self.pending_jobs.extend(jobs)
        print(self.pending_jobs)
        return self.schedule_next_job()

    def on_job_completion(self, jobs: list):
        for job in jobs:
            for task in job.tasks:
                self.deallocate(task)
            self.running_jobs.remove(job)
        return self.schedule_next_job()

    def schedule_next_job(self, choices=None):
        if self.pending_jobs != [] and self.idle_resources >= len(self.pending_jobs[0].tasks):
            print(f" {len(self.pending_jobs)} jobs pending")
            print(f" {self.idle_resources} resources available >= {len(self.pending_jobs[0].tasks)} tasks")
            if choices == None:
                choices = len(self.pending_jobs)
            print(f" Scheduling next job from {choices} choices")
            next_job = self.pending_jobs.pop(choices - 1)
            print(f" Scheduling job {next_job.id}")
            for task in next_job.tasks:
                self.allocate(task)
            self.simulator.schedule(next_job.tasks)
            self.running_jobs.append(next_job)
            print(f" Returning {choices - 1}")
            return choices - 1
        else:
            print(" No jobs to schedule")
            return None
