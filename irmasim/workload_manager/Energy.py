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
            'energy': lambda node, job: -node_energy(job, node),
            'edp': lambda node, job: -node_edp(job, node)
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

        viable_nodes.sort(key=lambda node: self.node_sort_key(node, job))

        selected_nodes = []
        if len(viable_nodes) >= job.nodes:
            while len(selected_nodes) < job.ntasks:
                node_count = min(job.ntasks - len(selected_nodes), job.nodes)
                selected_nodes.extend(viable_nodes[0:node_count])
        return selected_nodes

    def on_end_step(self):
        pass

    def on_end_simulation(self):
        pass


def node_energy(job: Job, node):
    energy = 0

    for i in range(job.ntasks_per_node):
        energy += node.cores()[i].dynamic_power

    energy += node.cores()[0].static_power
    energy *= job.req_time

    return energy

def node_edp(job: Job, node):
    return node_energy(job, node) * job.req_time
