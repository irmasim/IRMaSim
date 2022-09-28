"""
Defines HDeepRM managers, which are in charge of mapping Jobs to resources.
"""

import random
import heapq
from irmasim.Job_seq import Job_seq
from irmasim.Job_MPI import Job_MPI
from irmasim.Task import Task
from irmasim.Job import Job


class JobScheduler:
    """Selects Jobs from the Job Queue to be processed in the Platform.

The Job selection policy is defined by the sorting key. Only one job is peeked in order to check
for sufficient resources available for it.

Attributes:
    pending_jobs (list):
        Job Queue. All incoming jobs arrive in this data structure.
    nb_active_jobs (int):
        Number of Jobs being served by the Platform.
    nb_completed_jobs (int):
        Number of Jobs already served by the Platform.
    peeked_job (batsim.batsim.Job):
        Cached next Job to be processed. This saves sorting the Job Queue a second time.
    sorting_key (function):
        Key defining the Job selection policy.
    """

    def __init__(self, jobs_queue : heapq) -> None:
        self.jobs_queue = jobs_queue
        self.pending_jobs = []
        self.nb_active_jobs = 0
        self.nb_completed_jobs = 0
        self.peeked_job = None
        self.sorting_key = None
        self.jobs_running = []
        self.finished_jobs = []

    def peek_job(self) -> Job:
        """Returns a reference to the first selected job.

This is the first Job to be processed given the selected policy. This method does not remove the
Job from the Job Queue.

Returns:
    The reference to the first selected Job.
        """

        if not self.sorting_key:
            self.peeked_job = random.choice(self.pending_jobs)
        else:
            self.pending_jobs.sort(key=self.sorting_key)
            self.peeked_job = self.pending_jobs[0]
        return self.peeked_job

    def new_job(self, job: Job) -> None:
        """Inserts a new job in the queue.

By default, it is appended to the right end of the queue.

Args:
    job (batsim.batsim.Job):
        Incoming Job to be inserted into the Job Queue.
        """
        self.pending_jobs.append(job)
        #print()
        #print('Lista pending tasks: ')
        #for task in self.pending_jobs:
            #print('Task ' + str(task.id_task) + ', pending tasks: ' + str(task.pending_tasks))
        #print()

    def remove_job(self) -> None:
        """Removes the first selected job from the queue.

It uses the cached peeked Job for removal.
        """
        self.pending_jobs.remove(self.peeked_job)
        for task in self.pending_jobs:
            if task.job_type == 2 and self.peeked_job.job_type == 2 and self.peeked_job.job_id == task.job_id:
                task.task_executed()
        #print()
        #print('Lista pending tasks: ')
        #for task in self.pending_jobs:
            #print('Task ' + str(task.id_task) + ', pending tasks: ' + str(task.pending_tasks))
        #print()


    def show_first_job_in_queue(self) -> Job:
        return self.jobs_queue[0]

    def pop_first_job_in_queue(self) -> Job:
        return heapq.heappop(self.jobs_queue)

    def run_jobs(self, jobs : list, now : float) -> None:
        for i in jobs:
            i.start_running = now
        self.jobs_running.extend(jobs)

    def job_complete(self, job: Job, now: float):
        job.finish = now
        self.finished_jobs.append(job)
        self.jobs_running.remove(job)


    @property
    def nb_jobs_queue_left(self) -> int:
        return len(self.jobs_queue)


    @property
    def nb_pending_jobs(self) -> int:
        """int: Number of pending jobs, equal to the current length of the queue."""
        return len(self.pending_jobs)

    @property
    def nb_running_jobs(self) -> int:
        return len(self.pending_jobs)


class ResourceManager:
    """Selects Cores and maintains Core states for serving incoming Jobs.

The Core selection policy is defined by the sorting key. The Core Pool is filtered by this key
to obtain the required resources by the Job. Cores have a state, which describes their
availability as well as computational capability and power consumption. Core selection might
fail if there are not enough available resources for the selected Job.

Attributes:
    state_changes (dict):
        Maps Cores to P-state changes for sending to Batsim
    platform (dict):
        Resource Hierarchy for relations. See :class:`~hdeeprm.resource.Core` for fields.
    core_pool (list):
        Contains all Cores in the Platform for filtering.
    over_utilization (dict):
        Tracks over-utilizations of cores, memory capacity and memory bandwidth.
    sorting_key (function):
        Key defining the Core selection policy.
    """

    def __init__(self, platform: dict, core_pool: list, job_limits: dict, options : dict) -> None:
        self.platform = platform
        self.core_pool = sorted(core_pool) #TODO Ordered
        # Add the job resource requirement limits to the resource hierarchy
        self.platform['job_limits'] = job_limits
        self.options = options
        self.sorting_key = None

    def update_cores(self, time: float):
        for core in self.core_pool:
            core.update_completion(time)
            if core.state['job_remaining_ops'] == 0 and core.state['served_job'] is not None:
                core.state['served_job'].core_finish.append(core.id)
                self.update_state(core.state['served_job'], [core.id], "FREE", time)

    def get_resources(self, job: Job, now: float) -> list or None:
        """Gets a set of resources for the selected job.

State of resources change as they are being selected.

Args:
    job (batsim.batsim.Job):
        Job to be served by the selected Cores. Used for checking requirements.
    now (float):
        Current simulation time in seconds.

Returns:
    Set of Cores as a :class:`~procset.ProcSet`. None if not enough resources available.
        """
        prueba = []
        available = []

        # Save the temporarily selected cores. We might not be able to provide the
        # asked amount of cores, so we would need to return them back
        selected = []

        # las tareas MPI se pueden planificar en cualquier core libre del sistema
        if job.job_type == 2:
            available = [core for core in self.core_pool if not core.state['served_job']]

        copia = [ core for core in self.core_pool if not core.state['served_job']]

        #print('Id job: ' + str(job.job_id) + ', Job type: ' + str(job.job_type) + ', available: ' + str(len(available)))

        # se asigna el primer nodo que cumpla que tenga el numero suficiente de cores
        # first fit en vez de best fit

        print()

        if job.job_type == 1:
            i = 0
            while i < len(copia):
                prueba = []
                prueba.append(copia[i])
                for core in copia:
                    if core not in prueba and ((copia[i].processor)['node'])['id'] == ((core.processor)['node'])['id']:
                        prueba.append(core)
                if (len(prueba) >= job.resources):
                    break
                else:
                    i = i + len(prueba)

        # modifico lista available por si lo que hacia estaba mal no estar
        # tocandola innecesariamente
        if job.job_type == 1:
            available = prueba.copy()

        #print('Quedan por ejecutar ' + str(job.num_tasks_job_pending) + ' tareas')

        #print()
        #print('Len available: ' + str(len(available)))

        print('job ' + str(job.job_id))

        if job.job_type == 1 and len(available) < job.resources:
            print()
            print('ERROR: job ' + str(job.job_id))
            print('len available: ' + str(len(available)) + ', job resources: ' + str(job.resources))
            return None
        elif job.job_type == 2 and len(available) < job.pending_tasks:
            print()
            print('ERROR: task ' + str(job.id_task) + ' del job ' + str(job.job_id))
            print('len available: ' + str(len(available)) + ', pending tasks: ' + str(job.pending_tasks))
            return None

        # la ejecucion se bloquea si no hay recursos suficientes
        """if job.job_type == 1 and len(available) < job.resources:
            return None
        elif job.job_type == 2 and len(available) < len(job.tasks):
            return None"""

        for _ in range(job.resources):
            mem_available = [
                core for core in available if core.processor['node']['current_mem'] >= job.mem
            ]
            # Sorting is needed everytime we access since completed jobs or assigned cores
            # might have changed the state
            if mem_available:
                if not self.sorting_key:
                    selected_id = random.choice(mem_available).id
                else:
                    mem_available.sort(key=self.sorting_key)
                    selected_id = mem_available[0].id
                    # forma de comprobar que los jobs secuenciales esperan que haya un nodo con los cores suficientes
                    #selected_id = mem_available[len(mem_available) - 1].id (esta linea es mia, no del simulador)
                # Update the core state
                self.update_state(job, [selected_id], 'LOCKED', now)

                # Add its ID to the temporarily selected core buffer
                selected.append(selected_id)

                # prueba para ver la contencion de memoria
                """print('Capacidad de memoria del nodo: ')
                print((mem_available[0].processor)['node']['max_mem'])
                print()
                print('Memoria utilizada por las tareas del job: ')
                print(job.profile['mem'])
                print()"""

                available = [core for core in available if core.id not in selected]
            else:
                # There are no sufficient resources, revert the state of the
                # temporarily selected
                print("Memoria Insuficiente")
                self.update_state(job, selected, 'FREE', now, free_resource_job=True)
                return None

            #TODO: arreglar este codigo
            print()
            if job.job_type == 1:
                print('Job ' + str(job.job_id) + ': planificado')
            elif job.job_type == 2:
                print('Task ' + str(job.id_task) + ': planificada del job ' + str(job.job_id))
            print('Se ejecuta en los cores: ')
            for id in selected:
                print(id)

        return selected

    def update_state(self, job: Job, id_list: list, new_state: str, now: float, free_resource_job : bool = False) -> None:
        """Modifies the state of the computing resources.

This affects speed, power and availability for selection. Modifications are local to the Decision
System until communicated to the Simulator. Modifying the state of a Core might trigger alterations
on Cores in the same Processor or Node scope due to shared resources.

Args:
    job (batsim.batsim.Job):
        Job served by the selected Cores. Used for updating resource contention.
    id_list (list):
        IDs of the Cores to be updated directly.
    new_state (str):
        Either "LOCKED" (makes Cores unavailable) or "FREE" (makes Cores available).
    now (float):
        Current simulation time in seconds.

Returns:
    A dictionary with all directly and indirectly modified Cores. Keys are the Cores IDs, values are
    the new P-states.
        """

        # Modify states of the cores
        # Associate each affected core with a new P-State

        """print('Cores cuyos estados van a ser modificados')
        for id in id_list:
            print('core ' + str(id) + ', estado ' + str(new_state))"""

        for id in id_list:
            score = self.core_pool[id]
            processor = score.processor
            if new_state == 'LOCKED':
                job.allocation.append(id)
                score.set_state("RUN", now, new_served_job=job)
                served_jobs_processor = 0

                for lcore in processor['local_cores']:
                    # If this is the first active core in the processor,
                    # set the state of the rest of cores to number_p_states (indirect energy consumption)
                    if lcore.state['served_job'] is None:
                        lcore.set_state("NEIGHBOURS-RUNNING", now)
                    else:
                        served_jobs_processor += 1

                self.overutilization_mem_bw_change_speed(now, processor,
                                                         served_jobs_processor, job)

            elif new_state == 'FREE':

                if free_resource_job:
                    job.allocation = []
                score.set_state("NEIGHBOURS-RUNNING", now)
                all_inactive = all(not lcore.state['served_job']
                                   for lcore in processor['local_cores'])

                served_jobs_processor = 0
                for lcore in processor['local_cores']:
                    # If this was the last core being utilized, lower all
                    # cores of processor from indirect energy consuming
                    if all_inactive:
                        lcore.set_state("IDLE", now)
                    if lcore.state['served_job'] != None:
                        served_jobs_processor += 1

                self.overutilization_mem_bw_change_speed(now, processor,
                                                         served_jobs_processor, job)

            else:
                raise ValueError('Error: unknown state')

            """elif new_state == 'FREE' and job.job_type == 3:

                for core in self.core_pool:
                    if core.state['served_job'] and core.state['served_job'].job_id == job.job_id:
                        if job.pending_tasks == 1:

                            if free_resource_job:
                                core.state['served_job'].allocation = []
                            core.set_state("NEIGHBOURS-RUNNING", now)
                            all_inactive = all(not lcore.state['served_job']
                                               for lcore in processor['local_cores'])

                            served_jobs_processor = 0
                            for lcore in processor['local_cores']:
                                # If this was the last core being utilized, lower all
                                # cores of processor from indirect energy consuming
                                if all_inactive:
                                    lcore.set_state("IDLE", now)
                                if lcore.state['served_job'] != None:
                                    served_jobs_processor += 1

                            self.overutilization_mem_bw_change_speed(now, processor,
                                                                     served_jobs_processor, job)
                        # TODO: probando a arreglar cosas
                        core.state['current_gflops'] = 0"""



    def overutilization_mem_bw_change_speed(self, now, processor,
                                            served_jobs_processor, job):
        # Check mem_bw in proccessor
        for lcore in processor['local_cores']:
            # If the memory bandwidth capacity is now overutilized,
            # transition every active core of the processor into another state(reduced GFLOPS)
            if lcore.state['served_job'] is not None:

                x = processor['current_mem_bw']
                y = lcore.state['current_mem_bw']
                n = served_jobs_processor - 1

                def ss(x):
                    if x < 0:
                        return 1
                    elif x > 1:
                        return 0
                    else:
                        return (1 - x*x*x*(x*(x*6-15)+10))

                def d(y, n):
                    aux = (y-(lcore.da-n)*lcore.db)/(lcore.dc-n*lcore.dd)
                    aux = ss(aux)
                    return aux * (n*0.6/(1+n*0.6))+1/(1+n*0.6)

                def perf(x, y, n):
                    if x < lcore.c:
                        return 1
                    elif x > ((d(y,n)+lcore.b*lcore.c-1)/lcore.b):
                        return d(y,n)
                    else:
                        return lcore.b*(x-lcore.c)+1

                # cambiando los speedups
                speedup_mem = round(perf(x, y, n),9)
                speedup_comm = self.overutilization_comm_bw_change_speed(now, processor, served_jobs_processor, job)

                if lcore.state['served_job'].job_type == 1:
                    speedup = speedup_mem
                elif lcore.state['served_job'].job_type == 2:
                    speedup = ((1 - lcore.state['served_job'].t_compute) * speedup_comm) + (speedup_mem * lcore.state['served_job'].t_compute)

                lcore.set_state("RUN", now, speedup=speedup)

                with open('{0}/speedup.log'.format(self.options['output_dir']), 'a') as f_speed:
                    f_speed.write(f'{lcore.id},{speedup},{now},{lcore.state["served_job"].name}, {x}, {y},{n}\n')

    def overutilization_comm_bw_change_speed(self, now, processor, served_jobs_processor, job) -> float:

        node_task = processor['node']
        speedup = 1
        tasks = []


        id_node = len(node_task['local_processors'])
        #print()
        #print('Node ' + str(id_node))

        """for processor in processor['node']['local_processors']:
            for core in processor['local_cores']:
                print('Core id ' + str(core.id) + ', comm_vol ' + str(core.state['current_comm_vol']))"""

        # recorrido de todos los cores de la plataforma
        for node in processor['node']['cluster']['local_nodes']:
            if node != node_task:
                node_comm_vol = 0
                for processor in node['local_processors']:
                    for core in processor['local_cores']:
                        if core.state['current_comm_vol'] > 0 and core.state['served_job'].job_id == job.job_id:
                            #print('EXISTE OTRA TAREA CON LA QUE COMUNICARSE')
                            node_comm_vol = node_comm_vol + core.state['current_comm_vol']
            else:
                for processor in node['local_processors']:
                    for core in processor['local_cores']:
                        if core.state['served_job'] and core.state['served_job'].job_id == job.job_id and core.state['served_job'] not in tasks:
                            tasks.append(core.state['served_job'])
                            #print('Sumando core ' + str(core.id))

        node_comm_vol = node_comm_vol * len(tasks)
        node['current_comm_vol'] = node_comm_vol
        """print('num tasks node: ' + str(num_task_node))
        print('node comm vol: ' + str(node_comm_vol))
        print()"""

        if node_comm_vol > node_task['comm_vol']:
            print()
            print('Se esta superando el comm bw del nodo ' + str(id_node) + ' por culpa del job ' + str(job.job_id))
            print('node comm vol ini: ' + str(node_comm_vol / len(tasks)) + ', num tasks node ' + str(len(tasks)))
            print('Node comm bw: ' + str(node_task['comm_vol']) + ', node comm vol: ' + str(node_comm_vol))
            speedup = 0.8

        return speedup
