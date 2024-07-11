from irmasim.workload_manager.Minimal import Minimal
from irmasim.Job import Job
from irmasim.Task import Task
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from irmasim.Simulator import Simulator

class Hesitant(Minimal):
    def __init__(self, simulator: 'Simulator'):
        super(Hesitant, self).__init__(simulator)

    def on_job_submission(self, jobs: list):
        self.pending_jobs.extend(jobs)

    def on_job_completion(self, jobs: list):
        for job in jobs:
            for task in job.tasks:
                self.deallocate(task)
            self.running_jobs.remove(job)

    def get_choices(self):
        if self.pending_jobs != []:
            return [ (job,None) for job in range(len(self.pending_jobs)) if len(self.pending_jobs[job].tasks) <= self.idle_resources ]
        else:
            return []

    def schedule_choice(self, choice):
        next_job = self.pending_jobs.pop(choice[0])
        assert self.idle_resources >= len(next_job.tasks)
        for task in next_job.tasks:
            self.allocate(task)
        self.simulator.schedule(next_job.tasks)
        self.running_jobs.append(next_job)

    def __str__(self):
        return f"{hex(id(self))} pending: {len(self.pending_jobs)} running: {len(self.running_jobs)}"

