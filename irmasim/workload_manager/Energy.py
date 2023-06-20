from irmasim.workload_manager.WorkloadManager import WorkloadManager as WM
from irmasim.Job import Job
from typing import TYPE_CHECKING
from sortedcontainers import SortedList
from irmasim.Options import Options
import importlib

if TYPE_CHECKING:
    from irmasim.Simulator import Simulator

'''
Workload Manager that schedules tasks based on 
optimising energy consumption and/or energy efficiency
'''
class Energy(WM):
    def __init__(self, simulator: 'Simulator'):
        super(Energy, self).__init__(simulator)

        if simulator.platform.config["model"] != "modelV1":
            raise Exception("Heuristic workload manager needs a modelV1 platform")

        options = Options().get()

        job_selections = {
            'energy': {
                'lo_first': lambda job: job.req_energy * job.ntasks,
                'hi_first': lambda job: -(job.req_energy * job.ntasks)
            },
            'edp': {
                'lo_first': lambda job: job.req_energy * job.req_time * job.ntasks,
                'hi_first': lambda job: -(job.req_energy * job.req_time * job.ntasks)
            }
        }

        node_selections = {
            'energy': {
                'lo_first': lambda node, job: self.node_energy(job, node),
                'hi_first': lambda node, job: -self.node_energy(job, node),
            },
            'edp': {
                'lo_first': lambda node, job: self.node_edp(job, node),
                'hi_first': lambda node, job: -self.node_edp(job, node)
            }
        }

        if 'criterion' not in options['workload_manager']:
            self.criterion = 'energy'
        else:
            self.criterion = options["workload_manager"]["criterion"]

        if 'job_prio' not in options['workload_manager']:
            self.job_prio = 'lo_first'
        else:
            self.job_prio = options["workload_manager"]["job_prio"]

        if 'node_prio' not in options['workload_manager']:
            self.node_prio = 'lo_first'
        else:
            self.node_prio = options["workload_manager"]["node_prio"]

        print(self.job_prio, self.node_prio, self.criterion)

        self.pending_jobs = SortedList(key=job_selections[self.criterion][self.job_prio])
        self.running_jobs = SortedList(key=job_selections[self.criterion][self.job_prio])
        self.node_estimation = node_selections[self.criterion][self.node_prio]

        mod = importlib.import_module("irmasim.platform.models." + options["platform_model_name"] + ".Node")
        klass = getattr(mod, 'Node')
        self.resources = self.simulator.get_resources(klass)

        self.assigned_nodes = {node.id: 0 for node in self.resources}
        self.min_freq = min([node.cores()[0].clock_rate for node in self.resources])

    def on_job_submission(self, jobs: list):
        self.pending_jobs.update(jobs)
        self.schedule_jobs()
        pass


    # FIXME: esto se esta ejecutando todo el rato para
    # FIXME: el experimento 1 lo high ???, por que no
    # FIXME: terminan los 2 trabajos pero sí porque llama
    # FIXME: a este metodo
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
            selected_node = self.select_node(j)
            if selected_node is not None:
                for task in j.tasks:
                    for core in selected_node.cores():
                        if core.task is None:
                            task.allocate(core.full_id())
                            self.simulator.schedule([task])
                            break
                to_assign.append(j)
                self.assigned_nodes[selected_node.id] += 1

        for job in to_assign:
            self.pending_jobs.remove(job)
            self.running_jobs.add(job)



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
