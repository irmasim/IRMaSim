from irmasim.workload_manager.WorkloadManager import WorkloadManager
from irmasim.Job import Job
from irmasim.Task import Task
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from irmasim.Simulator import Simulator

class Minimal(WorkloadManager):
    def __init__(self, simulator: 'Simulator'):
        super(Minimal, self).__init__(simulator)
        if simulator.platform.config["model"] != "modelV1":
            raise Exception("Minimal workload manager needs a modelV1 platform")
        self.resources = [ [ resource_id, 1 ] for resource_id in self.simulator.get_resources_ids() ]
        self.idle_resources = len(self.resources)
        self.pending_jobs = []
        self.running_jobs = []

    def on_job_submission(self, jobs: list):
        self.pending_jobs.extend(jobs)
        while self.schedule_next_job():
            pass

    def on_job_completion(self, jobs: list):
        for job in jobs:
            for task in job.tasks:
                self.deallocate(task)
            self.running_jobs.remove(job)
        while self.schedule_next_job():
            pass

    def schedule_next_job(self):
        if self.pending_jobs != [] and self.idle_resources >= len(self.pending_jobs[0].tasks):
            next_job = self.pending_jobs.pop(0)
            for task in next_job.tasks:
                self.allocate(task)
            self.simulator.schedule(next_job.tasks)
            self.running_jobs.append(next_job)
            return True
        else:
            return False

    def on_end_step(self):
        pass

    def on_end_simulation(self):
        pass

    def allocate(self, task: Task):
        resource = 0
        while self.resources[resource][1] == 0:
            resource += 1
        self.resources[resource][1] = 0
        self.idle_resources -= 1
        task.allocate(self.resources[resource][0])

    def deallocate(self, task: Task):
        for resource in range(len(self.resources)):
           if self.resources[resource][1] == 0 and self.resources[resource][0] == task.resource:
               self.resources[resource][1] = 1
               self.idle_resources += 1
               break

