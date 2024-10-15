from irmasim.workload_manager.WorkloadManager import WorkloadManager
from irmasim.Job import Job
from irmasim.Task import Task
from irmasim.platform.BasicNode import BasicNode
from typing import TYPE_CHECKING
from irmasim.Options import Options
from sortedcontainers import SortedList
import importlib
import random as rand
import math

if TYPE_CHECKING:
    from irmasim.Simulator import Simulator

class BackfillBestFit(WorkloadManager):
    def __init__(self, simulator: 'Simulator'):
        super(BackfillBestFit, self).__init__(simulator)
        if simulator.platform.config["model"] != "modelV1":
            raise Exception("BackfillBestFit workload manager needs a modelV1 platform")
        options = Options().get()

        self.pending_jobs = []
        self.running_jobs = []

        self.backfilled_jobs = 0
        self.backfill_candidates = 0
        
        mod = importlib.import_module("irmasim.platform.models." + options["platform_model_name"] + ".Node")
        klass = getattr(mod, 'Node')

        self.pending_jobs = [] 
        self.running_jobs = []
        self.backfill_jobs = []
        #self.backfill_jobs = SortedList(key=job_criteria[self.job_selection])
        #self.node_estimation = node_criteria[self.node_selection]

        # Only used when all the nodes are idle
        if 'resource_selection' not in options['workload_manager']:
            self.node_selection = 'first'
        else:
            self.node_selection = options["workload_manager"]["resource_selection"]

        node_criteria = {
            'random': None, # Random is handled in the code
            'first': lambda node: node.id,
            'high_gflops': lambda node: - node.children[0].mops_per_core,
            'high_cores': lambda node: - node.count_cores(),
            'high_mem': lambda node: - node.current_memory,
            'high_mem_bw': lambda node: node.children[0].requested_memory_bandwidth,
            'low_power': lambda node: (node.children[0].children[0].static_power + node.children[0].children[0].dynamic_power) * node.count_cores(),
        }
        self.node_sort_key = node_criteria[self.node_selection]
        self.idle_nodes = []
        self.idle_nodes.extend(self.simulator.get_resources(klass))
        self.resources = self.simulator.get_resources(klass)

        self.assigned_nodes = {node.id: 0 for node in self.resources}
        self.min_freq = min([node.cores()[0].clock_rate for node in self.resources])

    def on_job_submission(self, jobs: list):
        self.pending_jobs.extend(jobs)
        print(f"[{self.simulator.simulation_time:.2f}] {[job.name for job in jobs]} submitted")
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
        
        # If there is no room for the first pending job, try to backfill the rest
        return self.try_backfill_jobs()
        
    def try_allocate_first_job(self):
        # Order the idle nodes according to the first job
        idle_nodes_ordered = self.order_idle_nodes()

        for node in idle_nodes_ordered:
            if node.count_idle_cores() >= len(self.pending_jobs[0].tasks):
                next_job = self.pending_jobs.pop(0)
                self.allocate(node, next_job)
                return True
        print(f"[{self.simulator.simulation_time:.2f}] Job {self.pending_jobs[0].name} cannot be allocated")
        return False
    
    def try_backfill_jobs(self):
        for job in self.pending_jobs.copy()[1:]:
            for node in self.order_idle_nodes():
                # Optimization: If the job does not fit in the node, do not check backfill
                if len(job.tasks) > node.count_cores():
                    continue
                # If the node is empty, backfill with the job (this will not affect the blocked job)
                if node.count_idle_cores() == node.count_cores():
                    self.backfill_jobs.append((job, node))
                # If the node is not empty, check if the job can be backfilled
                elif self.check_backfill(node, job):
                    self.backfill_jobs.append((job, node))

        if len(self.backfill_jobs) == 0:
            return False

        print(f"Initial backfill jobs: {[(job[0].name, job[1].id) for job in self.backfill_jobs]}")
        self.backfill_jobs.sort(key=lambda jobNode: self.best_fit(jobNode))
        self.backfill_candidates = len(self.backfill_jobs)
        print(f"Sorted backfill jobs: {[(jobNode[0].name, jobNode[1].id, self.best_fit(jobNode)) for jobNode in self.backfill_jobs]}")
        print()

        # If there are backfill jobs, allocate until there are no more room
        while len(self.backfill_jobs) > 0:
            job, node = self.backfill_jobs.pop(0)
            # If the job has been already allocated, skip it
            if job not in self.pending_jobs:
                continue
            # If the node is empty, it can't be blocked by any job (it will be allocated)
            if node.count_idle_cores() == node.count_cores():
                self.backfill_job(node, job)
            # It is possible that the job cannot be backfilled (the machine status has changed)
            elif self.check_backfill(node, job):
                self.backfill_job(node, job)
            else:
                print(f"[{self.simulator.simulation_time:.2f}] Job {job.name} cannot be backfilled anymore")
                continue
            # Recalculate priorities
            self.backfill_jobs.sort(key=lambda jobNode: self.best_fit(jobNode))
            print(f"Sorted backfill jobs: {[(jobNode[0].name, jobNode[1].id, self.best_fit(jobNode)) for jobNode in self.backfill_jobs]}")

        return False
    
    def backfill_job(self, node, job):
        self.backfilled_jobs += 1
        self.pending_jobs.remove(job)
        self.allocate(node, job)

    def order_idle_nodes(self):
        if self.node_selection != 'random':
            self.idle_nodes.sort(key=self.node_sort_key)
            return self.idle_nodes
        else:
            rand.shuffle(self.idle_nodes)
            return self.idle_nodes
    
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
        if node not in self.idle_nodes:
            self.idle_nodes.append(node)

    def shadow_time_and_extra_cores(self, node: BasicNode):
        running_jobs_eet_tmp = sorted(node.running_jobs(), key=lambda j: (j.start_time + j.req_time)) #ASC De menor a mayor
        # Remove repeated jobs
        running_jobs_eet = []
        for job in running_jobs_eet_tmp:
            if job not in running_jobs_eet:
                running_jobs_eet.append(job)
        idle_cores_after_end_job=node.count_idle_cores()
        # The start point of the blocking job is the end time of the last job in the list of blocking jobs
        blocking_job_start_point = running_jobs_eet[-1].start_time + running_jobs_eet[-1].req_time 
        for i, job in enumerate(running_jobs_eet):
            idle_cores_after_end_job += len(job.tasks)
            if idle_cores_after_end_job >= len(self.pending_jobs[0].tasks):
                blocking_job_start_point = job.start_time + job.req_time
                break
        # Extra nodes are the cores that will not be used by the blocking job neither by the actual running jobs
        extra_cores = node.count_cores() - len(self.pending_jobs[0].tasks)
        for job in running_jobs_eet[i+1:]: 
            extra_cores -= len(job.tasks)

        return blocking_job_start_point, extra_cores

    def check_backfill(self, node: BasicNode, job: Job):
        # shadow_time = Start time of the blocking job (until this time jobs can be backfilled)
        # extra_cores = Cores that will not be used by the blocking job and are not used
        shadow_time , extra_cores = self.shadow_time_and_extra_cores(node)
        # If there are enough cores for the job regardless of the cores that the blocking job(s) will use
        if len(job.tasks) <= extra_cores and len(job.tasks) <= node.count_idle_cores(): # (la segunda condicion es redundante¿?)
            return True
        # If there are enough cores for the job (using part of the ones is using blocking job) and the job ends before the blocking job
        elif len(job.tasks) <= node.count_idle_cores() and (self.simulator.simulation_time + job.req_time) <= shadow_time: 
            return True
        
        return False

    def best_fit(self, jobNode):
        job, node = jobNode
        # If the node is empty, return 0 (highest priority)
        if node.count_idle_cores() == node.count_cores():
            return 0
        shadow_time, extra_cores = self.shadow_time_and_extra_cores(node)
        spare_time = shadow_time
        if node.count_idle_cores() >= len(job.tasks):
            spare_time = shadow_time - job.req_time
        else:
            running_jobs = sorted(node.running_jobs(), key=lambda j: j.req_time)
            idle_cores = 0
            for running_job in running_jobs:
                idle_cores += len(running_job.tasks)
                if idle_cores >= job.ntasks:
                    spare_time = shadow_time - (running_job.start_time + running_job.req_time) - job.req_time
                    break
        return spare_time

    def node_energy(self, job: Job, node):
        node_info = node.cores()[0]

        dyn_fraction = 0
        for i in range(job.ntasks):
            dyn_fraction += node_info.dynamic_power

        running_node_jobs = self.assigned_nodes[node.id]
        static_fraction = 0
        for c in node.cores():
            static_fraction += c.static_power
        static_fraction /= (running_node_jobs + 1)

        node_time = job.req_time * self.estimate_speedup(node)
        energy = node_time * (dyn_fraction + static_fraction)

        return energy
    
    def node_edp(self, job: Job, node):
        node_time = job.req_time * self.estimate_speedup(node)
        energy = self.node_energy(job, node)
        
        return energy * node_time

    def estimate_speedup(self, node):
        node_info = node.cores()[0]
        freq_speedup = (self.min_freq / node_info.clock_rate)
        inverted_dpflops = ((node_info.clock_rate * 1e3) / node_info.mops)

        return freq_speedup * inverted_dpflops

    def header(klass):
        return "time,backfill_candidates,backfilled_jobs,pending_jobs"

    def log_state(self):
        log = f"{self.simulator.simulation_time:.2f},{self.backfill_candidates},{self.backfilled_jobs},{len(self.pending_jobs)}"
        self.backfilled_jobs = 0
        return log
