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
            'low_power': lambda node: (node.children[0].children[0].static_power + node.children[0].children[0].dynamic_power) * node.count_cores(),
            'energy_lowest': lambda node, job: self.node_energy(job, node),
            'energy_highest': lambda node, job: -self.node_energy(job, node),
            'edp_lowest': lambda node, job: self.node_edp(job, node),
            'edp_highest': lambda node, job: -self.node_edp(job, node)
        }

        self.node_sort_key = node_selections[self.node_scheduler]
        self.idle_nodes = []
        self.idle_nodes.extend(self.simulator.get_resources(klass))
        self.busy_nodes = []
        self.resources = self.simulator.get_resources(klass)
        print(f"Node selection: {self.node_scheduler}")

        self.assigned_nodes = {node.id: 0 for node in self.resources}
        self.min_freq = min([node.cores()[0].clock_rate for node in self.resources])

        #print(f"Nodo:", [node.id for node in self.idle_nodes], "Power:",
        #[(node.children[0].children[0].static_power + node.children[0].children[0].dynamic_power) * node.count_cores() for node in self.idle_nodes])

    def on_job_submission(self, jobs: list):
        self.pending_jobs.extend(jobs)
        #print(f"\n\n{self.simulator.simulation_time}: Llegan jobs: {[job.name for job in jobs]}")
        # Planifica jobs hasta que no haya mas nodos libres o no haya mas jobs
        while self.schedule_next_job():
            pass

    def on_job_completion(self, jobs: list):
        for job in jobs:
            for task in job.tasks:
                self.deallocate(task)
            self.running_jobs.remove(job)
            self.assigned_nodes[job.tasks[0].resource[2]] -= 1
            #print(f"\n\n{self.simulator.simulation_time}: Completa job: {job.name}")
        while self.schedule_next_job():
            pass

    def schedule_next_job(self):
        # Ïf there are no pending jobs or no idle nodes, return False
        if len(self.pending_jobs) == 0 or len(self.idle_nodes) == 0:
            return False
        
        idle_nodes_ordered = self.order_idle_nodes()

        if self.try_allocate_first_job(idle_nodes_ordered):
            return True
        
        # If there is no room for the first pending job, try to backfill the rest
        return self.try_backfill_jobs(idle_nodes_ordered)
    
    def order_idle_nodes(self):
        if self.node_scheduler != 'random':
            if (self.node_scheduler == 'energy_lowest' or self.node_scheduler == 'energy_highest' or 
                self.node_scheduler == 'edp_lowest' or self.node_scheduler == 'edp_highest'):
                for job in self.pending_jobs:
                    self.idle_nodes.sort(key=lambda node: self.node_sort_key(node, job))
            else:
                self.idle_nodes.sort(key=self.node_sort_key)
            return self.idle_nodes
        else:
            rand.shuffle(self.idle_nodes)
            return self.idle_nodes
        
    def try_allocate_first_job(self, idle_nodes_ordered):
        for node in idle_nodes_ordered:
            if node.count_idle_cores() >= len(self.pending_jobs[0].tasks):
                next_job = self.pending_jobs.pop(0)
                self.allocate(node, next_job)
                return True
        return False
    
    def try_backfill_jobs(self, idle_nodes_ordered):
        for job in self.pending_jobs.copy()[1:]:
            for node in self.idle_nodes.copy():
                # Optimization: If the job does not fit in the node, do not check backfill
                if len(job.tasks) > node.count_cores():
                    continue
                # If the node is empty, backfill with the job (this will not affect the blocked job)
                if node.count_idle_cores() == node.count_cores():
                    self.backfill_job(node, job)
                    break
                # If the node is not empty, check if the job can be backfilled
                elif self.check_backfill(node=node, job=job):
                    self.backfill_job(node, job)
                    break
        return False
    
    def backfill_job(self, node, job):
        backfill_job = job
        self.pending_jobs.remove(job)
        self.allocate(node, backfill_job)
    
    # Original function with more than 10 lines (and debugging prints)
    """
    def schedule_next_job(self):
        if len(self.pending_jobs) != 0 and len(self.idle_nodes):
            #print(f"\nScheduling next job. Jobs: {[job.name for job in self.pending_jobs]}")
            idle_nodes_ordered = []
            if self.node_scheduler != 'random':
                self.idle_nodes.sort(key=self.node_sort_key)
                idle_nodes_ordered = self.idle_nodes
                #print(f"Nodo:", [node.id for node in idle_nodes_ordered])
            else: 
                idle_nodes_ordered =  rand.shuffle(self.idle_nodes) 

            #for node in idle_nodes_ordered:
                #print(f"Nodo: {node.id} free: {node.count_idle_cores()} / {node.count_cores()}")

            for node in self.idle_nodes:
                #print(f"Nodo:",node.id ,"free:", node.count_idle_cores(), "pending_job[0] tasks:", len(self.pending_jobs[0].tasks))
                if node.count_idle_cores() >= len(self.pending_jobs[0].tasks):
                    next_job = self.pending_jobs.pop(0)
                    #print(f"job: ", next_job.name, "future jobs:", len(self.pending_jobs))
                    #print(f"ENTRA PRIMERO", next_job.name)
                    self.allocate(node, next_job) # Como se que el job entra, la funcion alocata cada task
                    #print(f"Nodo:",node.id ,"entra job:", next_job.name, "free:", node.count_idle_cores(), "/", node.count_cores())
                    return True 
            
            #print(f"No hay espacio para el job:", self.pending_jobs[0].name, "resto:", [job.name for job in self.pending_jobs[1:]])
            # There is no room for the first pending job
            # Removing the blocking job (the first) and trying to backfill the rest
            for job in self.pending_jobs.copy()[1:]:
                # La lista se modificara en el bucle
                #print(f"Probando backfill para el job: {job.name} con {len(job.tasks)} tasks")
                for node in self.idle_nodes.copy():
                    # Optimización: Si el job no cabe en el nodo, no se comprueba el backfill
                    if len(job.tasks) > node.count_cores():
                        continue
                    #print(f"en el nodo: {node.id} libres: {node.count_idle_cores()} / {node.count_cores()}")
                    # Si el nodo esta vacio, hace backfill con el job
                    if node.count_idle_cores() == node.count_cores():
                        backfill_job = job
                        self.pending_jobs.remove(job)
                        self.allocate(node, backfill_job)
                        #print(f"Nodo vacio:",node.id ,"backfill del job:", job.name,"free:", node.count_idle_cores())
                        break
                    elif self.check_backfill(node=node, job=job):
                        # print(f"BACKFILL: ", job.id)
                        backfill_job = job
                        self.pending_jobs.remove(job)
                        self.allocate(node, backfill_job) #Como se que el job entra, la funcion alocata cada task y actualiza listas
                        #print(f"Nodo:",node.id ,"backfill del job:", job.name,"free:", node.count_idle_cores())
                        break
                        #if node.count_idle_cores() == 0:
                        #    break #Si el nodo esta ocupado, Rompemos for de los jobs, y intentamos backfill en el resto de nodos
            #print(f"Jobs restantes:", [job.name for job in self.pending_jobs])
            return False
        else:
            #print(f"No hay mas jobs o nodos libres")
            return False
    """

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
            self.assigned_nodes[node.id] += 1

    def deallocate(self, task: Task):
        core = self.simulator.get_resource(list(task.resource))
        node = core.parent.parent
        #print(f"node : ", node)
        if node in self.busy_nodes:
            self.busy_nodes.remove(node)
            self.idle_nodes.append(node)

    def shadow_time_and_extra_nodes (self, node: BasicNode):
        running_jobs_eet_tmp = sorted(node.running_jobs(), key=lambda j: (j.start_time + j.req_time)) #ASC De menor a mayor
        # Remove repeated jobs
        running_jobs_eet = []
        for job in running_jobs_eet_tmp:
            if job not in running_jobs_eet:
                running_jobs_eet.append(job)
        #print(f"\trunning_jobs_eet:", [j.name for j in running_jobs_eet])
        #print([j.name for j in running_jobs_eet])
        # Inicializa los cores libres con los actuales
        idle_cores_after_end_job=node.count_idle_cores()
        # Si el nodo no tiene suficientes cores para ejecutrar el bloqueante 
        # se pone como start point cuando finaliza el ultimo job en lista eet
        blocking_job_start_point = running_jobs_eet[-1].start_time + running_jobs_eet[-1].req_time 
        extra_nodes = 0
        for i in range(len(running_jobs_eet)): #Busco el start time del next job que es = estimated end time de algun running job
            #print(f"idle_cores_after_end_job:", idle_cores_after_end_job, "pending_jobs:", len(self.pending_jobs[0].tasks))
            idle_cores_after_end_job += len(running_jobs_eet[i].tasks) # Sumo los cores que se liberan al finalizar el job
            if idle_cores_after_end_job >= len(self.pending_jobs[0].tasks): # Si hay suficientes cores para el job bloqueante 
                #print(f"limit job: ", running_jobs_eet[i].name)
                #print(f"limmit job: ", running_job.name)
                blocking_job_start_point = running_jobs_eet[i].start_time + running_jobs_eet[i].req_time # Start point del job bloqueante
                #print(f"start point: ", blocking_job_start_point)
                break

        extra_nodes = node.count_cores() -  len(self.pending_jobs[0].tasks)
        #print(f"extra_nodes:", extra_nodes, "running_jobs_eet[i+1:]:", [job.name for job in running_jobs_eet[i+1:]])
        for job in running_jobs_eet[i+1:]: 
            extra_nodes -= len(job.tasks)


        return blocking_job_start_point, extra_nodes

    def check_backfill(self, node: BasicNode, job: Job):

        # shadow_time = Start time of the blocking job (until this time jobs can be backfilled)
        # extra_nodes = Nodes that will not be used by the blocking job and are not used
        shadow_time , extra_nodes = self.shadow_time_and_extra_nodes(node)
        #print(f"shadow_time:", shadow_time, "extra_nodes:", extra_nodes, "job", job.name, "end time:", self.simulator.simulation_time + job.req_time)
        
        # Si hay suficientes cores para el job independientemente de los que vaya a usar el job bloqueado
        if len(job.tasks) <= extra_nodes and len(job.tasks) <= node.count_idle_cores(): # (la segunda condicion es redundante¿?)
            return True
        # Si hay suficientes cores para el job (utilizando parte de los del bloqueante) y el job termina antes del job bloqueante
        elif len(job.tasks) <= node.count_idle_cores() and (self.simulator.simulation_time + job.req_time) <= shadow_time: 
            return True
        #print(f"\tno se puede backfill (shadow_time: {shadow_time}, extra_nodes: {extra_nodes})")
        return False

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