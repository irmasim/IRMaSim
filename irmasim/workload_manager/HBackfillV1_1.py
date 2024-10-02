from irmasim.workload_manager.WorkloadManager import WorkloadManager
from irmasim.Job import Job
from irmasim.Task import Task
from irmasim.platform.BasicNode import BasicNode
from typing import TYPE_CHECKING
from irmasim.Options import Options
from sortedcontainers import SortedList
import importlib
import random as rand

if TYPE_CHECKING:
    from irmasim.Simulator import Simulator

class HBackfillV1_1(WorkloadManager):
    def __init__(self, simulator: 'Simulator'):
        super(HBackfillV1_1, self).__init__(simulator)
        if simulator.platform.config["model"] != "modelV1_1":
            raise Exception("HBackfillV1_1 workload manager needs a modelV1 platform")
        options = Options().get()

        mod = importlib.import_module("irmasim.platform.models." + options["platform_model_name"] + ".Node")
        klass = getattr(mod, 'Node')

        if 'job_selection' not in options['workload_manager']:
            self.job_selection = 'first'
        else:
            self.job_selection = options["workload_manager"]["job_selection"]

        if 'node_selection' not in options['workload_manager']:
            self.node_selection = 'first'
        else:
            self.node_selection = options["workload_manager"]["node_selection"]
        
        job_criteria = {
            'first': lambda job: job.id,
            'random': lambda job: job.id,
            'energy_lowest': lambda job: job.req_energy * job.ntasks,
            'energy_highest': lambda job: -(job.req_energy * job.ntasks),
            'edp_lowest': lambda job: job.req_energy * job.req_time * job.ntasks,
            'edp_highest': lambda job: -(job.req_energy * job.req_time * job.ntasks)
        }

        node_criteria = {
            'random': lambda node: node.id,
            'first': lambda node: node.id,
            'high_gflops': lambda node: - node.children[0].mops_per_node,
            'high_cores': lambda node: - node.cores,
            'high_mem': lambda node: - node.current_memory,
            'high_mem_bw': lambda node: node.children[0].requested_memory_bandwidth,
            'low_power': lambda node: (node.children[0].children[0].static_power + node.children[0].children[0].dynamic_power) * node.cores,
            'energy_lowest': lambda node, job: self.node_energy(job, node),
            'energy_highest': lambda node, job: -self.node_energy(job, node),
            'edp_lowest': lambda node, job: self.node_edp(job, node),
            'edp_highest': lambda node, job: -self.node_edp(job, node)
        }

        self.energy_criteria = ['energy_lowest', 'energy_highest', 'edp_lowest', 'edp_highest']

        self.pending_jobs = [] 
        self.running_jobs = []
        self.backfill_jobs = SortedList(key=job_criteria[self.job_selection])
        #self.node_estimation = node_criteria[self.node_selection]

        self.node_sort_key = node_criteria[self.node_selection]
        self.idle_nodes = []
        self.idle_nodes.extend(self.simulator.get_resources(klass))
        resources = self.simulator.get_resources(klass)
        self.resources = [ [ resource.full_id(), resource.config['cores'], resource.config['cores'] ] for resource in resources ] 
        print(f"Job selection: {self.job_selection}")
        print(f"Node selection: {self.node_selection}")
        # Print the resources values

        self.assigned_nodes = {node.id: 0 for node in resources}
        self.min_freq = min([node.clock_rate for node in resources])

    def on_job_submission(self, jobs: list):
        self.pending_jobs.extend(jobs)
        print(f"[{self.simulator.simulation_time:.2f}] {[job.id for job in jobs]} submitted")
        # Planifica jobs hasta que no haya mas nodos libres o no haya mas jobs
        while self.schedule_next_job():
            pass

    def on_job_completion(self, jobs: list):
        for job in jobs:
            print(f"[{self.simulator.simulation_time:.2f}] Job {job.name} in node {job.tasks[0].resource[2]} completed")
            for task in job.tasks:
                self.deallocate(task)
            self.running_jobs.remove(job)
            self.assigned_nodes[job.tasks[0].resource[2]] -= 1
        print()
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
        idle_nodes_ordered = self.order_idle_nodes(self.pending_jobs[0])

        for node in idle_nodes_ordered:
            if node.idle_cores() >= len(self.pending_jobs[0].tasks):
                next_job = self.pending_jobs.pop(0)
                self.allocate(node, next_job)
                print(f"[{self.simulator.simulation_time:.2f}] First job {next_job.name} allocated to node {node.id} (idle cores: {node.idle_cores()})")
                return True
        return False
    
    def try_backfill_jobs(self):
        for job in self.pending_jobs.copy()[1:]:
            for node in self.order_idle_nodes(job):
                # Optimization: If the job does not fit in the node, do not check backfill
                if len(job.tasks) > node.cores:
                    continue
                # If the node is empty, backfill with the job (this will not affect the blocked job)
                if node.idle_cores() == node.cores:
                    self.backfill_job(node, job)
                    break
                # If the node is not empty, check if the job can be backfilled
                elif self.check_backfill(node, job):
                    #self.backfill_job(node, job)
                    self.backfill_jobs.add(job)
                    break
       
        print(f"[{self.simulator.simulation_time:.2f}] {len(self.backfill_jobs)} jobs can be backfilled: ", end="")
        for job in self.backfill_jobs:
            print(f"{job.name}", end=" ")
        print()

        # If there are backfill jobs, allocate until there are no more room
        while len(self.backfill_jobs) > 0:
            job = self.backfill_jobs.pop(0)
            for node in self.order_idle_nodes(job):
                if len(job.tasks) <= node.idle_cores():
                    self.backfill_job(node, job)
                    break
        self.backfill_jobs.clear()
 
        return False
    
    def backfill_job(self, node, job):
        self.pending_jobs.remove(job)
        self.allocate(node, job)

    def order_idle_nodes(self, job):
        if self.node_selection != 'random':
            if self.node_selection in self.energy_criteria:
                self.idle_nodes.sort(key=lambda node: self.node_sort_key(node, job))
            else:
                self.idle_nodes.sort(key=self.node_sort_key)
            return self.idle_nodes
        else:
            rand.shuffle(self.idle_nodes)
            return self.idle_nodes
    
    def on_end_step(self):
        pass

    def on_end_simulation(self):
        pass    

    def allocate(self, node, job):
        print(f"[{self.simulator.simulation_time:.2f}] Job {job.name} allocated to node {node.id} (idle cores: {node.idle_cores()})")
        # Get the resource from the list of resources with the same node id 
        resource_index = -1
        for resource in range(len(self.resources)):
            if self.resources[resource][0] == node.full_id():
                resource_index = resource
                break
        for task in job.tasks:
            task.allocate(self.resources[resource_index][0])
        self.simulator.schedule(job.tasks)
        self.running_jobs.append(job)

    def deallocate(self, task):
        for resource in range(len(self.resources)):
            if self.resources[resource][0] == task.resource:
                self.resources[resource][1] += 1
                if self.resources[resource][1] == self.resources[resource][2]:
                    self.idle_nodes.append(self.resources[resource])

    def shadow_time_and_extra_cores (self, node: BasicNode):
        node_running_jobs = [job for job in self.running_jobs if job.tasks[0].resource[2] == node.id] 
        running_jobs_eet_tmp = sorted(node_running_jobs, key=lambda j: (j.start_time + j.req_time)) #ASC De menor a mayor
        # Remove repeated jobs
        running_jobs_eet = []
        for job in running_jobs_eet_tmp:
            if job not in running_jobs_eet:
                running_jobs_eet.append(job)
        idle_cores_after_end_job=node.idle_cores()
        # The start point of the blocking job is the end time of the last job in the list of blocking jobs
        blocking_job_start_point = running_jobs_eet[-1].start_time + running_jobs_eet[-1].req_time 
        for i, job in enumerate(running_jobs_eet):
            idle_cores_after_end_job += len(job.tasks)
            if idle_cores_after_end_job >= len(self.pending_jobs[0].tasks):
                blocking_job_start_point = job.start_time + job.req_time
                break
        # Extra nodes are the cores that will not be used by the blocking job neither by the actual running jobs
        extra_cores = node.cores -  len(self.pending_jobs[0].tasks)
        for job in running_jobs_eet[i+1:]: 
            extra_cores -= len(job.tasks)

        return blocking_job_start_point, extra_cores

    def check_backfill(self, node: BasicNode, job: Job):

        # shadow_time = Start time of the blocking job (until this time jobs can be backfilled)
        # extra_cores = Cores that will not be used by the blocking job and are not used
        shadow_time , extra_cores = self.shadow_time_and_extra_cores(node)
        
        # If there are enough cores for the job regardless of the cores that the blocking job(s) will use
        if len(job.tasks) <= extra_cores and len(job.tasks) <= node.idle_cores(): # (la segunda condicion es redundante¿?)
            return True
        # If there are enough cores for the job (using part of the ones is using blocking job) and the job ends before the blocking job
        elif len(job.tasks) <= node.idle_cores() and (self.simulator.simulation_time + job.req_time) <= shadow_time: 
            return True
        
        return False

    def node_energy(self, job: Job, node):
        node_info = node.cores[0]

        dyn_fraction = 0
        for i in range(job.ntasks):
            dyn_fraction += node_info.dynamic_power

        running_node_jobs = self.assigned_nodes[node.id]
        static_fraction = 0
        for c in node.cores:
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
        node_info = node.cores[0]
        freq_speedup = (self.min_freq / node_info.clock_rate)
        inverted_dpflops = ((node_info.clock_rate * 1e3) / node_info.mops)

        return freq_speedup * inverted_dpflops
