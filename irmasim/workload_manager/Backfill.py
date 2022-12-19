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

class Backfill(WorkloadManager):
    def __init__(self, simulator: 'Simulator'):
        super(Backfill, self).__init__(simulator)
        if simulator.platform.config["model"] != "modelV1":
            raise Exception("Backfill workload manager needs a modelV1 platform")
        options = Options().get()

        self.pending_jobs = []
        self.running_jobs = []
        
        mod = importlib.import_module("irmasim.platform.models." + options["platform_model_name"] + ".Node")
        klass = getattr(mod, 'Node')

        if not "resource_selection" in options["workload_manager"]:
            self.node_scheduler = 'first'
        else:
            self.node_scheduler = options["workload_manager"]["resource_selection"]

        node_selections = {
            'random': lambda node: node.id,
            'first': lambda node: node.id,
            'high_gflops': lambda node: - node.children[0].mops_per_node,
            'high_cores': lambda node: - node.count_cores(),
            'high_mem': lambda node: - node.current_memory,
            'high_mem_bw': lambda node: node.children[0].requested_memory_bandwidth,
            'low_power': lambda node: (node.children[0].children[0].static_power + node.children[0].children[0].dynamic_power) * node.count_cores()
        }

        self.node_sort_key = node_selections[self.node_scheduler]
        self.idle_nodes = []
        self.idle_nodes.extend(self.simulator.get_resources(klass))
        self.busy_nodes = []
        print(f"Node selection: {self.node_scheduler}")

        #print(f"Nodo:", [node.id for node in self.idle_nodes], "Power:",
        #[(node.children[0].children[0].static_power + node.children[0].children[0].dynamic_power) * node.count_cores() for node in self.idle_nodes])

        
    def on_job_submission(self, jobs: list):
        self.pending_jobs.extend(jobs)
        while self.schedule_next_job():
            pass

    def on_job_completion(self, jobs: list):
        for job in jobs:
            for task in job.tasks:
                self.deallocate(task)
            self.running_jobs.remove(job)
        while self.schedule_next_job():
            pass

    def schedule_next_job(self):
        if len(self.pending_jobs) != 0 and len(self.idle_nodes):
            idle_nodes_ordered = []
            if self.node_scheduler != 'random':
                self.idle_nodes.sort(key=self.node_sort_key)
                idle_nodes_ordered = self.idle_nodes
                #print(f"Nodo:", [node.id for node in idle_nodes_ordered])
            else: 
                idle_nodes_ordered =  rand.shuffle(self.idle_nodes) 

            for node in self.idle_nodes:
                if node.count_idle_cores() >= len(self.pending_jobs[0].tasks):
                    next_job = self.pending_jobs.pop(0)
                    #print(f"job: ", next_job.name, "future jobs:", len(self.pending_jobs))
                    #print(f"ENTRA PRIMERO", next_job.name)
                    self.allocate(node, next_job) # Como se que el job entra, la funcion alocata cada task
                    print(f"Nodo:",node.id ,"ENTRA PRIMERO: ", next_job.name, "free:", node.count_idle_cores())
                    return True #primer trabajo planificado perfect
            
            #Ningun nodo tiene espacio para pending_jobs[0]
            #Quitando el job que bloquea (el primero)
            for job in self.pending_jobs.copy()[1:]:
             #La lista se modificara en el bucle
                     for node in self.idle_nodes.copy():
                        if self.check_backfill(node=node, job=job):
                            # print(f"BACKFILL: ", job.id)
                            backfill_job = job
                            self.pending_jobs.remove(job)
                            self.allocate(node, backfill_job) #Como se que el job entra, la funcion alocata cada task y actualiza listas
                            print(f"Nodo:",node.id ,"BACKFILL: ", job.name,"free:", node.count_idle_cores())
                            if node.count_idle_cores() == 0:
                                break #Si el nodo esta ocupado, Rompemos for de los jobs, y intentamos backfill en el resto de nodos

            return False
        else:
            return False

    def on_end_step(self):
        pass

    def on_end_simulation(self):
        pass    

    def allocate(self, node: BasicNode, job: Job):
            cores = node.idle_cores() 
            for task in job.tasks:
                task.allocate(cores.pop(0).full_id())

            self.simulator.schedule(job.tasks)
            self.running_jobs.append(job)
            if node.count_idle_cores() == 0:
                self.idle_nodes.remove(node)
                self.busy_nodes.append(node)
                #print("Nodo saturado")

    def deallocate(self, task: Task):
        core = self.simulator.get_resource(list(task.resource))
        node = core.parent.parent
        #print(f"node : ", node)
        if node in self.busy_nodes:
            self.busy_nodes.remove(node)
            self.idle_nodes.append(node)

    def shadow_time_and_extra_nodes (self, node: BasicNode):
        running_jobs_eet = sorted(set(node.running_jobs()), key=lambda j: (j.start_time + j.req_time)) #ASC De menor a meyor
        #print([j.name for j in running_jobs_eet])
        idle_cores_after_end_job=node.count_idle_cores()
        #Si el nodo no tiene suficientes cores para ejecutrar el bloqueante 
        # se pone como start point cuando finaliza el ultimo job en lista eet
        blocking_job_start_point = running_jobs_eet[-1].start_time + running_jobs_eet[-1].req_time 
        extra_nodes = 0
        for i in range(len(running_jobs_eet)): #Busco el start time del next job que es = estimated end time de algun running job
            #print(f"idle_cores = ", idle_cores_after_end_job)
            idle_cores_after_end_job += len(running_jobs_eet[i].tasks)
            if idle_cores_after_end_job >= len(self.pending_jobs[0].tasks):
                #print(f"limmit job: ", running_job.name)
                blocking_job_start_point = running_jobs_eet[i].start_time + running_jobs_eet[i].req_time
                break

        extra_nodes = node.count_cores() -  len(self.pending_jobs[0].tasks)
        for job in running_jobs_eet.copy()[i+1:]: 
            extra_nodes -= len(job.tasks)


        return blocking_job_start_point, extra_nodes

    def check_backfill(self, node: BasicNode, job: Job):

        #extra_nodes = Nodes that will not be used by the blocking job and are not used
        shadow_time , extra_nodes = self.shadow_time_and_extra_nodes(node)

        if len(job.tasks) <= extra_nodes and len(job.tasks) <= node.count_idle_cores():
            return True
        elif len(job.tasks) <= node.count_idle_cores() and (self.simulator.simulation_time + job.req_time) <= shadow_time:
            return True

        return False
