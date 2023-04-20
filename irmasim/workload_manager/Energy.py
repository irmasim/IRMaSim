from irmasim.workload_manager.WorkloadManager import WorkloadManager as WM
from irmasim.Job import Job
from typing import TYPE_CHECKING
from sortedcontainers import SortedList
from irmasim.Options import Options
import importlib

if TYPE_CHECKING:
    from irmasim.Simulator import Simulator

'''
TODO: Documentar esto
'''
class Energy(WM):
    def __init__(self, simulator: 'Simulator'):
        super(Energy, self).__init__(simulator)

        if simulator.platform.config["model"] != "modelV1":
            raise Exception("Heuristic workload manager needs a modelV1 platform")

        options = Options().get()

        if not "job_selection" in options["workload_manager"]:
            self.job_scheduler = 'energy'
        else:
            self.job_scheduler = options["workload_manager"]["job_selection"]

        if not "resource_selection" in options["workload_manager"]:
            self.node_scheduler = 'energy'
        else:
            self.node_scheduler = options["workload_manager"]["resource_selection"]

        job_selections = {
            'energy': lambda job: -job.req_energy,
            'edp': lambda job: -job.req_energy*job.req_time
        }

        node_selections = {
            'energy': lambda node, job, min_freq: -node_energy(job, node, min_freq),
            'edp': lambda node, job, min_freq: -node_edp(job, node, min_freq)
        }

        self.pending_jobs = SortedList(key=job_selections[self.job_scheduler])
        self.running_jobs = SortedList(key=job_selections[self.job_scheduler])
        self.node_sort_key = node_selections[self.node_scheduler]

        mod = importlib.import_module("irmasim.platform.models." + options["platform_model_name"] + ".Node")
        klass = getattr(mod, 'Node')
        self.resources = self.simulator.get_resources(klass)
        print(f"Job selection: {self.job_scheduler}")

    def on_job_submission(self, jobs: list):

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

        if not selected_nodes:
            return False

        for task, node in zip(next_job.tasks, selected_nodes):
            for core in node.cores():
                if core.task is None:
                    task.allocate(core.full_id())
                    self.simulator.schedule([task])
                    break

        self.pending_jobs.remove(next_job)
        self.running_jobs.add(next_job)
        return True

    def layout_job(self, job: Job):
        viable_nodes = [node for node in self.resources if node.count_idle_cores() >= job.ntasks_per_node]
        min_freq = min([node.cores()[0].clock_rate for node in self.resources])
        viable_nodes.sort(key=lambda node: self.node_sort_key(node, job, min_freq))

        selected_nodes = []
        if len(viable_nodes) >= job.nodes:
            while len(selected_nodes) < job.ntasks:
                node_count = min(job.ntasks - len(selected_nodes), job.nodes)
                selected_nodes.extend(viable_nodes[0:node_count])
        return selected_nodes

    def on_end_step(self):
        pass

    def on_end_simulation(self):
        a = self.simulator.energy_consumption_statistics()
        b = self.simulator.simulation_time_statistics()

        print("Simulation EDP:", a["total"]*b["total"])
        pass


def node_energy(job: Job, node, min_freq):
    energy = 0
    node_time = job.req_time * (node.cores()[0].clock_rate/min_freq) * (1/node.cores()[0].mops)

    for i in range(job.ntasks_per_node):
        energy += node.cores()[i].dynamic_power + node.cores()[i].static_power

    energy *= node_time  # TODO: Arreglar el calculo de dpflops, que ahora está en mops (pdflops x clock_rate x 1000)

    return energy


def node_edp(job: Job, node, min_freq):
    node_time = job.req_time * (node.cores()[0].clock_rate/min_freq) * (1/node.cores()[0].mops)
    return node_energy(job, node, min_freq) * node_time
