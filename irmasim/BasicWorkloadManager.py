from irmasim.Job import Job
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from irmasim.Simulator import Simulator


class BasicWorkloadManager:

    def __init__(self, simulator: 'Simulator'):
        self.simulator = simulator
        self.idle_resources = self.simulator.get_resources()
        self.busy_resources = []
        self.pending_jobs = []
        self.running_jobs = []

    def on_job_submission(self, jobs: list):
        self.pending_jobs.extend(jobs)
        while self.schedule_next_job():
            pass

    def on_job_completion(self, job: Job):
        for task in job.tasks:
            self.busy_resources.remove(task.resource)
            self.idle_resources.append(task.resource)
        while self.schedule_next_job():
            pass

    def schedule_next_job(self):
        if len(self.idle_resources) >= len(self.pending_jobs[0].tasks):
            next_job = self.pending_jobs.pop(0)
            for task in next_job.tasks:
                task.resource = self.idle_resources.pop(0)
                self.busy_resources.append(task.resource)
            self.simulator.schedule(next_job.tasks)
            self.running_jobs.append(next_job)
            return True
        else:
            return False
