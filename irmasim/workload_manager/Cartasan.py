from irmasim.workload_manager.WorkloadManager import WorkloadManager
from irmasim.Job import Job
from irmasim.Task import Task
from irmasim.platform.BasicNode import BasicNode
from typing import TYPE_CHECKING
from irmasim.Options import Options
import importlib
import random as rand

if TYPE_CHECKING:
    from irmasim.Simulator import Simulator

class Cartasan(WorkloadManager):
    def __init__(self, simulator: 'Simulator'):
        super(Cartasan, self).__init__(simulator)
        if simulator.platform.config["model"] != "modelV1" and simulator.platform.config["model"] != "modelV1_1":
            raise Exception("Cartasan workload manager needs a modelV1 platform")
        options = Options().get()

        self.pending_jobs = []
        self.running_jobs = []

        self.backfilled_jobs = 0
        
        mod = importlib.import_module("irmasim.platform.models." + options["platform_model_name"] + ".Node")
        klass = getattr(mod, 'Node')

        if 'algorithm' not in options['workload_manager']:
            self.algorithm = 'SAF'
        else:
            self.algorithm = options["workload_manager"]["algorithm"]

        if 'resource_selection' not in options['workload_manager']:
            self.node_selection = 'random'
        else:
            self.node_selection = options["workload_manager"]["resource_selection"]

        algorithm = {
            'SPF': lambda job: job.req_time, # Smallest Estimated Processing Time First
            'SQF': lambda job: job.ntasks, # Smallest Resource Requirement First
            'SAF': lambda job: job.req_time * job.ntasks  # Smalles Estimated "Area" First
        }

        node_criteria = {
            'random': None, # Random is handled in the code
            'first': lambda node: node.id,
            'high_gflops': lambda node: - node.children[0].mops_per_core,
            'low_power': lambda node: (node.children[0].children[0].static_power + node.children[0].children[0].dynamic_power) * node.count_cores()
        }

        self.pending_jobs = [] 
        self.running_jobs = []
        # Maximum time a job can be waiting in the queue before raising its priority to the highest
        self.threshold = 259200 # 3 days in seconds
        self.priority_queue = [] # TODO

        self.algorithm_sort_key = algorithm[options["workload_manager"]["algorithm"]]
        self.node_sort_key = node_criteria[self.node_selection]
        self.idle_nodes = []
        self.idle_nodes.extend(self.simulator.get_resources(klass))
        self.resources = self.simulator.get_resources(klass)
        print(f"Algorithm: {options["workload_manager"]["algorithm"]}")

        self.assigned_nodes = {node.id: 0 for node in self.resources}
        self.min_freq = min([node.cores()[0].clock_rate for node in self.resources])

    def on_job_submission(self, jobs: list):
        self.pending_jobs.extend(jobs)
        self.pending_jobs.sort(key=self.algorithm_sort_key)
        print(f"[{self.simulator.simulation_time:.2f}] {[job.id for job in jobs]} submitted")
        print(f"[{self.simulator.simulation_time:.2f}] Ordered jobs: {[job.id for job in self.pending_jobs]}")
        # Planifica jobs hasta que no haya mas nodos libres o no haya mas jobs
        while self.schedule_next_job():
            pass

    def on_job_completion(self, jobs: list):
        for job in jobs:
            print(f"[{self.simulator.simulation_time:.2f}] Job {job.name} completed")
            for task in job.tasks:
                self.deallocate(task)
            self.running_jobs.remove(job)
            self.assigned_nodes[job.tasks[0].resource[2]] -= 1
        while self.schedule_next_job():
            pass

    def schedule_next_job(self):
        # Ïf there are no pending jobs or no idle nodes, return False
        if len(self.pending_jobs) == 0 or len(self.idle_nodes) == 0:
            return False
        
        # If there is room for the first pending job, allocate it
        if self.try_allocate_first_job():
            return True
        
    def try_allocate_first_job(self):
        # Order the idle nodes according to the first job
        idle_nodes_ordered = self.order_idle_nodes(self.pending_jobs[0])

        for node in idle_nodes_ordered:
            if node.count_idle_cores() >= len(self.pending_jobs[0].tasks):
                next_job = self.pending_jobs.pop(0)
                self.allocate(node, next_job)
                return True
        #print(f"[{self.simulator.simulation_time:.2f}] Job {self.pending_jobs[0].name} blocked")
        return False
    
        
    def on_end_step(self):
        pass

    def on_end_simulation(self):
        pass    

    def allocate(self, node: BasicNode, job: Job):
        print(f"[{self.simulator.simulation_time:.2f}] Job {job.name} allocated to node {node.id}")
        cores = node.idle_cores() 
        for task in job.tasks:
            task.allocate(cores.pop(0).full_id())

        self.simulator.schedule(job.tasks)
        self.running_jobs.append(job)
        if node.count_idle_cores() == 0:
            self.idle_nodes.remove(node)
        self.assigned_nodes[node.id] += 1

    def deallocate(self, task: Task):
        core = self.simulator.get_resource(list(task.resource))
        node = core.parent.parent
        self.idle_nodes.append(node)


    def order_idle_nodes(self, job):
        if self.node_selection != 'random':
            self.idle_nodes.sort(key=self.node_sort_key)
        else:
            rand.shuffle(self.idle_nodes)
        return self.idle_nodes

    def header(klass):
        return "time,backfill_candidates,backfilled_jobs,pending_jobs,backfill_ext"

    def log_state(self):
        log = f"{self.simulator.simulation_time:.2f},{self.backfilled_jobs},{self.backfilled_jobs},{len(self.pending_jobs)},0"
        self.backfilled_jobs = 0
        return log

