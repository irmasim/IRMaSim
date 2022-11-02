import importlib
from irmasim.workload_manager.WorkloadManager import WorkloadManager
from irmasim.Job import Job
from irmasim.Task import Task
from irmasim.Options import Options
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from irmasim.Simulator import Simulator

class NodeWM(WorkloadManager):
    def __init__(self, simulator: 'Simulator'):
        super(NodeWM, self).__init__(simulator)
        if simulator.platform.config["model"] != "modelV2":
            raise Exception("NodeWM workload manager needs a modelV2 platform")
        options = Options().get()
        mod = importlib.import_module("irmasim.platform.models." + options["platform_model_name"] + ".Node")
        klass = getattr(mod, 'Node')
        resources = self.simulator.get_resources(klass)

        self.resources = [ [ resource.full_id(), resource.config['cores'] ] for resource in resources ]
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
        if self.pending_jobs != [] and max([ resource[1] for resource in self.resources ]) > 0:
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
        self.resources[resource][1] -= 1
        task.allocate(self.resources[resource][0])

    def deallocate(self, task: Task):
        for resource in range(len(self.resources)):
           if self.resources[resource][0] == task.resource:
               self.resources[resource][1] += 1
               break

