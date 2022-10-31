from irmasim.Job import Job
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from irmasim.Simulator import Simulator


class Basic:

    def __init__(self, simulator: 'Simulator'):
        self.simulator = simulator
        self.idle_resources = self.simulator.get_resources_ids()
        self.busy_resources = []
        self.pending_jobs = []
        self.running_jobs = []

    def on_job_submission(self, jobs: list):
        self.pending_jobs.extend(jobs)
        while self.schedule_next_job():
            pass

    def on_job_completion(self, jobs: list):
        for job in jobs:
            for task in job.tasks:
                self.busy_resources.remove(task.resource)
                # TODO mantener orden recursos
                self.idle_resources.insert(0, task.resource)
            self.running_jobs.remove(job)
        while self.schedule_next_job():
            pass

    def schedule_next_job(self):
        if self.pending_jobs != [] and len(self.idle_resources) >= len(self.pending_jobs[0].tasks):
            next_job = self.pending_jobs.pop(0)
            for task in next_job.tasks:
                task.allocate(self.idle_resources.pop(0))
                self.busy_resources.append(task.resource)
            self.simulator.schedule(next_job.tasks)
            self.running_jobs.append(next_job)
            return True
        else:
            return False

    def on_end_step(self):
        pass

    def on_end_simulation(self):
        pass
