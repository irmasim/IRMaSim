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

class Schedule:
    def __init__(self, node: int, job: Job, completion_time: float, idle_cores: int = 0):
        self.node = node
        self.job = job
        self.completion_time = completion_time
        self.idle_cores = 0
        self.running = False

    def __repr__(self):
        return "Schedule(node={}, job={}, completion_time={}, idle_cores={}, running={})".format(self.node, self.job.id, self.completion_time, self.idle_cores, self.running)

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
        self.nodes = self.simulator.get_resources(getattr(mod, "Node"))

        self.lowest_mops = min([ node.children[0].mops_per_core for node in self.nodes ])
        self.node_speedup = [ node.children[0].mops_per_core/self.lowest_mops for node in self.nodes]
        self.node_queue = [ [] for node in self.nodes ]

    def on_job_submission(self, jobs: list):
        min_min_scheduling = []
        max_min_scheduling = []

        if self.option == "duplex" or self.option == "min_min":
            sorted_jobs = SortedList(jobs, key=lambda job: job.req_time)
            min_min_scheduling = self.create_schedule(sorted_jobs)

        if self.option == "duplex" or self.option == "max_min":
            sorted_jobs = SortedList(jobs, key=lambda job: -job.req_time)
            max_min_scheduling = self.create_schedule(sorted_jobs)

        if self.option == "duplex":
            min_min_final_time = max([ sch.completion_time for sch in min_min_scheduling ])
            max_min_final_time = max([ sch.completion_time for sch in max_min_scheduling ])
            if min_min_final_time < max_min_final_time:
                self.option = "min_min"
            else:
                self.option = "max_min"

        if (self.option == "min_min"):
            for sch in min_min_scheduling:
                self.node_queue[sch.node].append(sch)
        else:
            for sch in max_min_scheduling:
                self.node_queue[sch.node].append(sch)
        self.schedule()

    def on_job_completion(self, jobs: list):
        for job in jobs:
            for n in range(0, len(self.nodes)):
                for sch in self.node_queue[n]:
                    if sch.job == job:
                        #print("Job ", job.id, " completed in node ", n, " at time ", self.simulator.simulation_time, " and the estimated completion time was ", sch.completion_time)
                        self.node_queue[n].pop(self.node_queue[n].index(sch))

        self.schedule()

    def schedule(self):
        for n in range(0, len(self.nodes)):
            for sch in self.node_queue[n]:
                node_idle_cores = self.nodes[n].count_idle_cores()
                if not sch.running and sch.job.ntasks_per_node <= node_idle_cores:
                    node_idle_cores -= sch.job.ntasks_per_node
                    sch.running = True
                    for task in sch.job.tasks:
                        for core in self.nodes[n].cores():
                            if core.task == None:
                                task.allocate(core.full_id())
                                self.simulator.schedule([task])
                                break # Go to next task


    def on_end_step(self):
        pass

    def on_end_simulation(self):
        pass

    def create_schedule(self, jobs: list):
        scheduling = []
        for job in jobs:
            best_completion_time = -1
            for i in range(0, len(self.nodes)):
                completion_time = self.calculate_completion_time(job, i, scheduling)
                if completion_time > 0:
                    if best_completion_time == -1 or completion_time < best_completion_time:
                        best_completion_time = completion_time
                        best_node = i
            scheduling.append(Schedule(best_node, job, best_completion_time))
        return scheduling

    def calculate_completion_time(self, job: Job, node: int, scheduling: list):
        if job.ntasks_per_node > self.nodes[node].count_cores():
            return -1
        if len(scheduling) != 0:
            return scheduling[-1].completion_time + job.req_time / self.node_speedup[node]
        if len(self.node_queue[node]) != 0:
            return self.node_queue[node][-1].completion_time + job.req_time / self.node_speedup[node]
        return self.simulator.simulation_time + job.req_time / self.node_speedup[node]

    def scheduler(self, jobs: list, scheduling: list):
        cores_times = copy.deepcopy(self.cores_times)

        for n in range(0, len(self.nodes)):
            scheduling.append([])

        for j in range(0, len(jobs)):
            cores_temporal_times = copy.deepcopy(cores_times)
            for n in range(0, len(self.nodes)):
                if len(self.nodes[n].cores()) < jobs[j].ntasks_per_node:
                    for c in range(len(cores_temporal_times[n])):
                        cores_temporal_times[n][c] = sys.maxsize
                    continue
                cores_task_times = sorted(cores_times[n])[:len(jobs[j].tasks)]
                base_time = cores_task_times[-1]
                if(self.simulator.simulation_time > base_time):
                    base_time = self.simulator.simulation_time
                for time_core in cores_task_times:
                    exec_time = jobs[j].req_time/self.node_speedup[n]
                    #exec_time = jobs[j].ops * jobs[j].opc * 1e-6 /(self.nodes[n].cores()[cores_temporal_times[n].index(time_core)].mops)
                    cores_temporal_times[n][cores_temporal_times[n].index(time_core)] = base_time + exec_time
            min_time = min(map(lambda x: max(x), cores_temporal_times))
            if min_time == sys.maxsize:
                continue
            for n in range(0 , len(self.nodes)):
                if min_time in cores_temporal_times[n]:
                    cores_times[n] = cores_temporal_times[n].copy()
                    scheduling[n].append(jobs[j])
                    break
        return cores_times
