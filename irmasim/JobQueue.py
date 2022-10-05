from irmasim.Job import Job
import math

class JobQueue:

    def __init__(self):
        self.future_jobs = []
        self.queued_jobs = []
        self.finished_jobs = []

    def add_job(self, job: Job):
        self.future_jobs.append(job)
        self.future_jobs.sort(key=lambda x: x.subtime)

    def add_jobs(self, jobs: list):
        self.future_jobs.extend(jobs)
        self.future_jobs.sort(key=lambda x: x.subtime)

    def get_next_jobs(self, now: float):
        if len(self.future_jobs) > 0:
            submitted_jobs = [job for job in self.future_jobs if job.subtime <= now]
            self.queued_jobs.extend(submitted_jobs)
            self.future_jobs = [job for job in self.future_jobs if job not in submitted_jobs]
            return submitted_jobs
        else:
            Exception("No jobs in queue")

    def get_next_step(self):
        if self.future_jobs:
            return self.future_jobs[0].subtime
        else:
            return math.inf

    def finish_jobs(self):
        finishing_jobs = [job for job in self.queued_jobs if job.is_job_finished()]
        self.finished_jobs.extend(finishing_jobs)
        self.queued_jobs = [job for job in self.queued_jobs if job not in finishing_jobs]
        return finishing_jobs
