"""
Defines HDeepRM managers, which are in charge of mapping Jobs to resources.
"""

import random
import heapq
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
        # TODO Change name to nb_jobs_running
        self.nb_active_jobs = 0
        #TODO Change name to nb_finished_jobs
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

    def remove_job(self) -> None:
        """Removes the first selected job from the queue.

It uses the cached peeked Job for removal.
        """
        self.pending_jobs.remove(self.peeked_job)

    def peek_job(self) -> Job:
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

        # Save the temporarily selected cores. We might not be able to provide the
        # asked amount of cores, so we would need to return them back
        selected = []

        available = [core for core in self.core_pool if not core.state['served_job']]
        if len(available) < job.resources:
            return None
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
                # Update the core state
                self.update_state(job, [selected_id], 'LOCKED', now)

                # Add its ID to the temporarily selected core buffer
                selected.append(selected_id)
                available = [core for core in available if core.id not in selected]
            else:
                # There are no sufficient resources, revert the state of the
                # temporarily selected
                print("Memoria Insuficiente")
                self.update_state(job, selected, 'FREE', now, free_resource_job=True)
                return None
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
                                                         served_jobs_processor)

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
                                                         served_jobs_processor)

            else:
                raise ValueError('Error: unknown state')

    def overutilization_mem_bw_change_speed(self, now, processor,
                                            served_jobs_processor):
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

                speedup = round(perf(x, y, n),9)

                lcore.set_state("RUN", now, speedup=speedup)

                with open('{0}/speedup.log'.format(self.options['output_dir']), 'a') as f_speed:
                    f_speed.write(f'{lcore.id},{speedup},{now},{lcore.state["served_job"].name}, {x}, {y},{n}\n')
