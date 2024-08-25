from irmasim.workload_manager.WorkloadManager import WorkloadManager
from irmasim.Job import Job
from irmasim.Task import Task
from typing import TYPE_CHECKING
from irmasim.Options import Options
import importlib

if TYPE_CHECKING:
    from irmasim.Simulator import Simulator

class HesitantShMem(WorkloadManager):
    def __init__(self, simulator: 'Simulator'):
        super(HesitantShMem, self).__init__(simulator)
        if simulator.platform.config["model"] != "modelV1":
            raise Exception("Heuristic workload manager needs a modelV1 platform")
        options = Options().get()

        self.pending_jobs = []
        self.running_jobs = []

        mod = importlib.import_module("irmasim.platform.models." + options["platform_model_name"] + ".Node")
        klass = getattr(mod, 'Node')
        self.resources = self.simulator.get_resources(klass)

    def on_job_submission(self, jobs: list):
        self.pending_jobs.extend(jobs)

    def on_job_completion(self, jobs: list):
        for job in jobs:
            self.running_jobs.remove(job)

    def get_choices(self):
        choices = []
        if self.pending_jobs != []: 
            print(f" {len(self.pending_jobs)} jobs pending")
            for i, job in enumerate(self.pending_jobs):
                for layout in self.layout_job(job):
                    choices.append((i,layout))
        return choices

    def schedule_choice(self, choice):
        next_job = self.pending_jobs[choice[0]]
        print(f" Scheduling job {next_job.id} {hex(id(next_job))}")
        layout = choice[1]
        for task,node in zip(next_job.tasks,layout):
            for core in self.resources[node].cores():
                if core.task == None:
                    task.allocate(core.full_id())
                    self.simulator.schedule([task])
                    break

        self.pending_jobs.remove(next_job)
        self.running_jobs.append(next_job)

    def layout_job(self, job: Job):
        viable_nodes = [ (i,node) for i,node in enumerate(self.resources) if node.count_idle_cores() >= job.ntasks_per_node ]
        unique = set()
        unique_viable_nodes = []
        for i, node in viable_nodes:
            if node.count_running_cores() == 0:
                attributes = f"{node.children[0].get_mops()}${node.count_cores()}"
                if attributes in unique:
                    continue
                else:
                    unique.add(attributes)
            unique_viable_nodes.append((i,node))
        layouts = []
        for i, node in unique_viable_nodes:
            layout = [ i for _ in range(job.ntasks_per_node) ]
            layouts.append(layout)
        return layouts
