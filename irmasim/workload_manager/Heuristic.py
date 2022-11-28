from irmasim.workload_manager.WorkloadManager import WorkloadManager
from irmasim.Job import Job
from irmasim.Task import Task
from typing import TYPE_CHECKING
from sortedcontainers import SortedList
from irmasim.Options import Options
import importlib
import random as rand

if TYPE_CHECKING:
    from irmasim.Simulator import Simulator

class Heuristic(WorkloadManager):
    def __init__(self, simulator: 'Simulator'):
        super(Heuristic, self).__init__(simulator)
        if simulator.platform.config["model"] != "modelV1":
            raise Exception("Heuristic workload manager needs a modelV1 platform")
        options = Options().get()

        if not "job_selection" in options["workload_manager"]:
            self.job_scheduler = 'first'
        else:
            self.job_scheduler = options["workload_manager"]["job_selection"]

        if not "core_selection" in options["workload_manager"]:
            self.core_scheduler = 'first'
        else:
            self.core_scheduler = options["workload_manager"]["core_selection"]

        job_selections = {
            'random': lambda job: job.id,
            'first': lambda job: job.submit_time,
            'shortest': lambda job: job.req_time,
            'smallest': lambda job: job.resources,
            'low_mem': lambda job: job.memory,
            'low_mem_ops': lambda job: job.memory_vol
        }

        core_selections = {
            'random': lambda core: core.parent.parent.id,
            'first': lambda core: core.parent.parent.id,
            'high_gflops': lambda core: - core.parent.mops_per_core,
            'high_cores': lambda core: - len([c for c in core.parent.children \
                                              if c.task is not None]),
            'high_mem': lambda core: - core.parent.parent.current_memory,
            'high_mem_bw': lambda core: core.parent.requested_memory_bandwidth,
            'low_power': lambda core: core.static_power + core.dynamic_power
        }

        self.pending_jobs = SortedList(key=job_selections[self.job_scheduler])
        self.running_jobs = SortedList(key=job_selections[self.job_scheduler])

        mod = importlib.import_module("irmasim.platform.models." + options["platform_model_name"] + ".Core")
        klass = getattr(mod, 'Core')
        self.idle_resources = []
        self.idle_resources.extend(self.simulator.get_resources(klass))
        self.busy_resources = []
        print(f"Job scheduler:", self.job_scheduler, ", Core scheduler:", self.core_scheduler)
        

    def on_job_submission(self, jobs: list):
        self.pending_jobs.update(jobs)
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
        if len(self.pending_jobs) != 0 and len(self.idle_resources) >= len(self.pending_jobs[0].tasks):
            if self.job_scheduler != "random":
                next_job = self.pending_jobs.pop(0)
            else: 
                next_job = rand.choice(self.pending_jobs)
                self.pending_jobs.remove(next_job)
            for task in next_job.tasks:
                self.allocate(task)
            #print(next_job.tasks.resource)
            self.simulator.schedule(next_job.tasks)
            self.running_jobs.add(next_job)
            return True
        else:
            return False

    def on_end_step(self):
        pass

    def on_end_simulation(self):
        pass

    def allocate(self, task: Task):
        if len(self.idle_resources) != 0:
            if self.core_scheduler != 'random':
                core = self.idle_resources.pop(0)
            else: 
                core = rand.choice(self.idle_resources)
                self.idle_resources.remove(core)
            self.busy_resources.append(core)
            task.allocate(core.full_id())

    def deallocate(self, task: Task):
        core = self.simulator.get_resource(list(task.resource))
        self.busy_resources.remove(core)
        self.idle_resources.append(core)
