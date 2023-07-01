from irmasim.workload_manager.WorkloadManager import WorkloadManager
from irmasim.Job import Job
from irmasim.Task import Task
from typing import TYPE_CHECKING
from sortedcontainers import SortedList
from irmasim.Options import Options
import importlib
import copy
import sys

if TYPE_CHECKING:
    from irmasim.Simulator import Simulator

class Duplex(WorkloadManager):
    def __init__(self, simulator: 'Simulator'):
        super(Duplex, self).__init__(simulator)
        if simulator.platform.config["model"] != "modelV1":
            raise Exception("Duplex workload manager needs a modelV1 platform")
        if "scheduling_option" not in Options().get()["workload_manager"]:
            self.option = "duplex"
        else:
            self.option = Options().get()["workload_manager"]["scheduling_option"] 
        if self.option != "duplex" and self.option != "min_min" and self.option != "max_min":
            raise Exception("Duplex workload manager needs a valid scheduling option")
        print("Using option: ", self.option)
        mod = importlib.import_module("irmasim.platform.models." + Options().get()["platform_model_name"] + ".Node")
        self.resources = self.simulator.get_resources(getattr(mod, "Node"))

        self.speedups = []
        self.base_sp_time = SortedList(self.resources, key=lambda node: node.children[0].mops_per_core)[0].children[0].mops_per_core
        self.scheduling = []
        self.cores_times = []
        for i in range(0, len(self.resources)):
            self.speedups.append(self.resources[i].children[0].mops_per_core/self.base_sp_time)
            self.scheduling.append([])
            self.cores_times.append([])
            for j in range(0, len(self.resources[i].cores())):
                self.cores_times[i].append(0)
        self.idle_cores = []
        for i in range(0, len(self.resources)):
            self.idle_cores.append(len(self.resources[i].cores()))
        self.running_jobs = []

    def on_job_submission(self, jobs: list):
        self.jobs = jobs.copy()
        min_min_planif = []
        max_min_planif = []

        if self.option == "duplex" or self.option == "min_min":
            planificating_jobs = SortedList(jobs, key=lambda job: job.req_time)
            min_min_times = self.scheduler(planificating_jobs, min_min_planif)

        if self.option == "duplex" or self.option == "max_min":
            planificating_jobs = SortedList(jobs, key=lambda job: 0 - job.req_time)
            max_min_times = self.scheduler(planificating_jobs, max_min_planif)

        if self.option == "duplex":
            min_min_exec_time = max(map(lambda x: max(x), min_min_times))
            max_min_exec_time = max(map(lambda x: max(x), max_min_times))
            if min_min_exec_time <= max_min_exec_time:
                self.option = "min_min"
            else:
                self.option = "max_min"
        if (self.option == "min_min"):
            self.cores_times = copy.deepcopy(min_min_times)
            for n in range (0, len(self.scheduling)):
                self.scheduling[n].extend(min_min_planif[n])
           
        if (self.option == "max_min"):
            self.cores_times = copy.deepcopy(max_min_times)
            for n in range (0, len(self.scheduling)):
                self.scheduling[n].extend(max_min_planif[n])
        for n in range(0, len(self.scheduling)):
            self.schedule_next_job(n)

    def on_job_completion(self, jobs: list):
        for job in jobs:
            for n in range(0, len(self.scheduling)):
                if job in self.scheduling[n]:
                    self.scheduling[n].pop(self.scheduling[n].index(job))
                    self.idle_cores[n] += job.ntasks_per_node
                    index_finished_job = self.running_jobs.index(job)
                    self.running_jobs.pop(index_finished_job)
                    self.schedule_next_job(n)
                    break

    def schedule_next_job(self, n: int):
        for job in self.scheduling[n]:
            if job not in self.running_jobs:
                if job.ntasks_per_node <= self.idle_cores[n]:
                    self.idle_cores[n] -= job.ntasks_per_node
                    self.running_jobs.append(job)
                    for task in job.tasks:
                        for core in self.resources[n].cores():
                            if core.task == None:
                                task.allocate(core.full_id())
                                self.simulator.schedule([task])
                                break
                else:
                    break

    def on_end_step(self):
        pass

    def on_end_simulation(self):
        pass
    

    def scheduler(self, jobs: list, scheduling: list):
        cores_times = copy.deepcopy(self.cores_times)

        for n in range(0, len(self.resources)):
            scheduling.append([])

        for j in range(0, len(jobs)):
            cores_temporal_times = copy.deepcopy(cores_times)
            for n in range(0, len(self.resources)):
                if len(self.resources[n].cores()) < jobs[j].ntasks_per_node:
                    for c in range(len(cores_temporal_times[n])):
                        cores_temporal_times[n][c] = sys.maxsize
                    continue
                cores_task_times = sorted(cores_times[n])[:len(jobs[j].tasks)]
                base_time = cores_task_times[-1]
                if(self.simulator.simulation_time > base_time):
                    base_time = self.simulator.simulation_time
                for time_core in cores_task_times:
                    exec_time = jobs[j].req_time/self.speedups[n]
                    #exec_time = jobs[j].ops * jobs[j].opc * 1e-6 /(self.resources[n].cores()[cores_temporal_times[n].index(time_core)].mops)
                    cores_temporal_times[n][cores_temporal_times[n].index(time_core)] = base_time + exec_time
            min_time = min(map(lambda x: max(x), cores_temporal_times))
            if min_time == sys.maxsize:
                continue
            for n in range(0 , len(self.resources)):
                if min_time in cores_temporal_times[n]:
                    cores_times[n] = cores_temporal_times[n].copy()
                    scheduling[n].append(jobs[j])
                    break
        return cores_times
