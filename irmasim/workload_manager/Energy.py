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

        # Definition of the different scheduling policies for jobs and nodes
        job_selections = {
            'energy': lambda job: job.req_energy,
            'edp': lambda job: job.req_energy * job.req_time
        }

        node_selections = {
            'energy': lambda node, job: self.node_energy(job, node),
            'edp': lambda node, job: self.node_edp(job, node)
        }

        # Choose energy prioritisation as default job and node scheduler
        if not "policy" in options["workload_manager"]:
            self.policy = 'energy'
        else:
            self.policy = options["workload_manager"]["job_selection"]


        # The job lists are sorted using one of the scheduling policies
        # (nodes with the lower "score" are given preference)
        self.pending_jobs = SortedList(key=job_selections[self.policy])
        self.running_jobs = SortedList(key=job_selections[self.policy])
        self.node_sort_key = node_selections[self.policy]

        mod = importlib.import_module("irmasim.platform.models." + options["platform_model_name"] + ".Node")
        klass = getattr(mod, 'Node')
        self.resources = self.simulator.get_resources(klass)

        # An auxiliary list that keeps track of the number of jobs running in a node
        self.assigned_nodes = {node.id: 0 for node in self.resources}

        # The frequency of the slowest node in the cluster
        self.min_freq = min([node.cores()[0].clock_rate for node in self.resources])

        print(f"Job selection: {self.policy}")

    '''
    Method that simulates the arrival of a new job to the scheduler
    The job is added to the pending list
    '''
    def on_job_submission(self, jobs: list):

        self.pending_jobs.update(jobs)
        while self.schedule_next_job():
            pass

    '''
    Method that simulates the end of a running job in the cluster
    The job is removed from the running jobs list and
    the job counter of the assigned node is updated
    '''
    def on_job_completion(self, jobs: list):
        for job in jobs:
            self.assigned_nodes[job.tasks[0].resource[2]] -= 1
            self.running_jobs.remove(job)

        while self.schedule_next_job():
            pass

    '''
    Method that schedules a pending job
    The job chosen is the one with the lowest score (according to
    the chosen scheduling policy)
    '''
    def schedule_next_job(self):
        if len(self.pending_jobs) == 0:
            return False

        # Get the next best pending job
        next_job = self.pending_jobs[0]

        # Get the list of nodes to which send the job
        selected_nodes = self.layout_job(next_job)

        # If the list is empty, do not schedule
        if not selected_nodes:
            return False

        # Each core of the node is assigned one of the tasks of the job
        # until there are no more tasks to assign (doesnt necessarily fill
        # all the cores in the node)
        for task, node in zip(next_job.tasks, selected_nodes):
            for core in node.cores():
                if core.task is None:
                    task.allocate(core.full_id())
                    self.simulator.schedule([task])
                    break

        # Move the job from pending to running
        self.pending_jobs.remove(next_job)
        self.running_jobs.add(next_job)
        return True

    '''
    Method that decides to which node the job to be scheduled can be assigned to
    '''
    def layout_job(self, job: Job):

        # Get all the nodes with enough free cores to run the job
        viable_nodes = [node for node in self.resources if node.count_idle_cores() >= job.ntasks_per_node]
        # Sort those jobs by the scheduling policy chosen, the lowest score is given priority
        viable_nodes.sort(key=lambda node: self.node_sort_key(node, job))

        # Of all the viable nodes, select the best ones, until the tasks of the job are all assigned
        selected_nodes = []
        if len(viable_nodes) >= job.nodes:
            while len(selected_nodes) < job.ntasks:
                node_count = min(job.ntasks - len(selected_nodes), job.nodes)
                selected_nodes.extend(viable_nodes[0:node_count])

        # Update the list of jobs assigned to nodes if nodes have been chosen
        # (For now we assume that only one node is selected at a time, so
        # we only update the first selected node)
        if selected_nodes:
            self.assigned_nodes[selected_nodes[0].id] += 1

        return selected_nodes

    def on_end_step(self):
        pass

    def on_end_simulation(self):
        pass

    '''
    Method that estimates the energy consumption of a job if it were to
    be assigned to a certain node 
    '''
    def node_energy(self, job: Job, node):
        node_info = node.cores()[0]

        freq_speedup = (self.min_freq/node_info.clock_rate)
        inverted_dpflops = ((node_info.clock_rate * 1e3)/node_info.mops)

        # Estimated execution time in node
        node_time = job.req_time * freq_speedup * inverted_dpflops

        # Get the dynamic power of all the cores to be occupied
        dyn_fraction = 0
        for i in range(job.ntasks_per_node):
            dyn_fraction += node_info.dynamic_power

        running_node_jobs = self.assigned_nodes[node.id]

        # The fraction of the static power that the job will use
        # Will vary depending on the amount of assigned jobs to the node
        static_fraction = 0
        for c in node.cores():
            static_fraction += c.static_power
        static_fraction /= (running_node_jobs + 1)

        # Estimated energy consumption
        energy = node_time * (dyn_fraction + static_fraction)
        return energy

    '''
    Method that estimates a jobs energy efficiency on a given node
    '''
    def node_edp(self, job: Job, node):
        node_info = node.cores()[0]
        freq_speedup = (self.min_freq / node_info.clock_rate)
        inverted_dpflops = ((node_info.clock_rate * 1e3) / node_info.mops)

        # Estimated execution time in node
        node_time = job.req_time * freq_speedup * inverted_dpflops

        energy = self.node_energy(job, node)

        return energy * node_time
