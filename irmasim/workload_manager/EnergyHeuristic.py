from irmasim.workload_manager.WorkloadManager import WorkloadManager as WM
from irmasim.Job import Job
from typing import TYPE_CHECKING
from sortedcontainers import SortedList
from irmasim.Options import Options
import importlib

if TYPE_CHECKING:
    from irmasim.Simulator import Simulator

class EnergyHeuristic(WM):
    def __init__(self, simulator: 'Simulator'):
        super(EnergyHeuristic, self).__init__(simulator)

        if simulator.platform.config["model"] != "modelV1":
            raise Exception("Heuristic workload manager needs a modelV1 platform")

        options = Options().get()

        job_criteria = {
            'timetasks': {
                'lowest': lambda job: job.req_time * job.ntasks,
                'highest': lambda job: -(job.req_time * job.ntasks)
            },
            'energy': {
                'lowest': lambda job: job.req_energy * job.ntasks,
                'highest': lambda job: -(job.req_energy * job.ntasks)
            },
            'edp': {
                'lowest': lambda job: job.req_energy * job.req_time * job.ntasks,
                'highest': lambda job: -(job.req_energy * job.req_time * job.ntasks)
            }
        }

        resource_criteria = {
            'energy': {
                'lowest': lambda node, job: self.node_energy(job, node),
                'highest': lambda node, job: -self.node_energy(job, node),
            },
            'edp': {
                'lowest': lambda node, job: self.node_edp(job, node),
                'highest': lambda node, job: -self.node_edp(job, node)
            }
        }

        if 'metric' not in options['workload_manager']:
            self.metric = 'energy'
        else:
            self.metric = options["workload_manager"]["metric"]

        if 'job_selection' not in options['workload_manager']:
            self.job_selection = 'lowest'
        else:
            self.job_selection = options["workload_manager"]["job_selection"]

        if 'resource_selection' not in options['workload_manager']:
            self.resource_selection = 'lowest'
        else:
            self.resource_selection = options["workload_manager"]["resource_selection"]

        print(self.job_selection, self.resource_selection, self.metric)

        self.pending_jobs = SortedList(key=job_criteria[self.metric][self.job_selection])
        self.running_jobs = SortedList(key=job_criteria[self.metric][self.job_selection])
        self.node_estimation = resource_criteria[self.metric][self.resource_selection]

        mod = importlib.import_module("irmasim.platform.models." + options["platform_model_name"] + ".Node")
        klass = getattr(mod, 'Node')
        self.resources = self.simulator.get_resources(klass)

        self.assigned_nodes = {node.id: 0 for node in self.resources}
        self.min_freq = min([node.cores()[0].clock_rate for node in self.resources])

    def on_job_submission(self, jobs: list):
        self.pending_jobs.update(jobs)
        self.schedule_jobs()
        pass

    def on_job_completion(self, jobs: list):
        for job in jobs:
            self.assigned_nodes[job.tasks[0].resource[2]] -= 1
            self.running_jobs.remove(job)
        if len(jobs) > 0:
            self.schedule_jobs()
        pass

    def schedule_jobs(self):
        to_assign = []

        for j in self.pending_jobs:
            if (self.simulator.simulation_time - j.submit_time) >= 60:
                to_assign = self.assign_job(j, to_assign)

        for job in to_assign:
            self.pending_jobs.remove(job)
            self.running_jobs.add(job)

        to_assign = []

        for j in self.pending_jobs:
            to_assign = self.assign_job(j, to_assign)

        for job in to_assign:
            self.pending_jobs.remove(job)
            self.running_jobs.add(job)

    def assign_job(self, j, assigned_list):
        selected_node = self.select_node(j)
        if selected_node is not None:
            for task in j.tasks:
                for core in selected_node.cores():
                    if core.task is None:
                        task.allocate(core.full_id())
                        self.simulator.schedule([task])
                        break
            assigned_list.append(j)
            self.assigned_nodes[selected_node.id] += 1
        return assigned_list

    def select_node(self, job):
        selected_node = None
        best = float('inf')

        for node in self.resources:
            if node.count_idle_cores() >= job.ntasks_per_node:
                estimate = self.node_estimation(node, job)
                if estimate < best:
                    best = estimate
                    selected_node = node

        return selected_node

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
