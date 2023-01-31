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

        if not "resource_selection" in options["workload_manager"]:
            self.node_scheduler = 'first'
        else:
            self.node_scheduler = options["workload_manager"]["resource_selection"]

        job_selections = {
            'random': lambda job: job.rand,
            'first': lambda job: job.submit_time,
            'shortest': lambda job: job.req_time,
            'smallest': lambda job: job.ntasks,
            'low_mem': lambda job: job.memory,
            'low_mem_ops': lambda job: job.memory_vol
        }

        node_selections = {
            'random': lambda node: node.id,
            'first': lambda node: node.id,
            'high_gflops': lambda node: - node.children[0].mops_per_core,
            'high_cores': lambda node: - node.count_idle_cores(),
            'high_mem': lambda node: - node.current_memory,
            'high_mem_bw': lambda node: node.children[0].requested_memory_bandwidth,
            'low_power': lambda node: - node.max_power_consumption()
        }

        self.pending_jobs = SortedList(key=job_selections[self.job_scheduler])
        self.running_jobs = SortedList(key=job_selections[self.job_scheduler])
        self.node_sort_key = node_selections[self.node_scheduler]

        mod = importlib.import_module("irmasim.platform.models." + options["platform_model_name"] + ".Node")
        klass = getattr(mod, 'Node')
        self.resources = self.simulator.get_resources(klass)
        #print("\n".join([ f'{node.id}: {node.max_power_consumption()}' for node in self.resources]))
        print(f"Job selection: {self.job_scheduler}, Node selection: {self.node_scheduler}")
        

    def on_job_submission(self, jobs: list):
        for job in jobs:
           job.rand=rand.random()
        self.pending_jobs.update(jobs)
        while self.schedule_next_job():
            pass

    def on_job_completion(self, jobs: list):
        for job in jobs:
            self.running_jobs.remove(job)
        while self.schedule_next_job():
            pass

    def schedule_next_job(self):
        if len(self.pending_jobs) == 0:
            return False
        next_job = self.pending_jobs[0]
        selected_nodes = self.layout_job(next_job)
        if selected_nodes == []:
            return False

        for task,node in zip(next_job.tasks,selected_nodes):
            for core in node.cores():
                if core.task == None:
                    task.allocate(core.full_id())
                    self.simulator.schedule([task])
                    break

        self.pending_jobs.remove(next_job)
        self.running_jobs.add(next_job)
        return True

    def layout_job(self, job: Job):
        viable_nodes = [ node for node in self.resources if node.count_idle_cores() >= job.ntasks_per_node ]

        if self.node_scheduler == 'random':
            rand.shuffle(viable_nodes)
        else:
            viable_nodes.sort(key=self.node_sort_key)
        selected_nodes = []
        if len(viable_nodes) >= job.nodes:
            while len(selected_nodes) < job.ntasks:
                node_count = min(job.ntasks-len(selected_nodes), job.nodes)
                selected_nodes.extend(viable_nodes[0:node_count])
        return selected_nodes

    def on_end_step(self):
        pass

    def on_end_simulation(self):
        pass


