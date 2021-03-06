import heapq
import math

# TODO Consider removing the entrypoints folder/package
from irmasim.entrypoints.HDeepRMWorkloadManager import HDeepRMWorkloadManager
from irmasim.manager import JobScheduler, ResourceManager
from irmasim.Job import Job
from irmasim.Statistics import Statistics


class Simulator:

    def __init__(self, job_limits: dict, jobs_queue: heapq, core_pool: list, platform: dict, options: dict):
        self.job_scheduler = JobScheduler(jobs_queue)
        self.resource_manager = ResourceManager(platform, core_pool, job_limits, options)
        self.scheduler = HDeepRMWorkloadManager(options, self)
        self.statistics = Statistics(options)
        self.simulation_time = 0
        self.start_simulation()

    def start_simulation(self) -> None:
        first_job = self.job_scheduler.pop_first_job_in_queue()
        self.simulation_time = first_job.subtime
        self.statistics.calculate_energy_and_edp(self.resource_manager.core_pool, self.simulation_time)
        self.scheduler.onJobSubmission(first_job)
        self.job_scheduler.new_job(first_job)
        self.start_static_jobs()

    def start_static_jobs(self) -> None:

        while self.job_scheduler.nb_jobs_queue_left > 0:

            self.peek_jobs_now()
            self.finish_jobs_now()
            self.scheduler.onNoMoreEvents()
            next_step = self.calculate_next_scheduler_step()
            self.statistics.calculate_energy_and_edp(self.resource_manager.core_pool,
                                                     round(next_step - self.simulation_time,9),
                                                     all_jobs_scheduler=(self.job_scheduler.nb_jobs_queue_left == 0
                                                                         and self.job_scheduler.nb_pending_jobs == 0))
            self.simulation_time = next_step
            self.resource_manager.update_cores(self.simulation_time)

        self.complete_all_jobs()


    def complete_all_jobs(self) -> None:

        while len(self.job_scheduler.jobs_running) > 0 or len(self.job_scheduler.pending_jobs) > 0:
            self.finish_jobs_now()
            self.scheduler.onNoMoreEvents()
            next_step = self.calculate_next_scheduler_step()
            if next_step != float("inf"):
                self.statistics.calculate_energy_and_edp(self.resource_manager.core_pool,
                                                         round(next_step - self.simulation_time,9),
                                                         all_jobs_scheduler=self.job_scheduler.nb_pending_jobs == 0)
                self.simulation_time = next_step
                self.resource_manager.update_cores(self.simulation_time)
        self.end_simulation()

    def end_simulation(self) -> None:
        self.scheduler.onSimulationEnds()
        self.statistics.write_results(self.simulation_time, self.job_scheduler.finished_jobs)
        print("Finish Simulation")

    def nb_pending_jobs(self) -> int:
        return self.job_scheduler.nb_pending_jobs

    def finish_jobs_now(self) -> None:
        finish_jobs = []
        for job in self.job_scheduler.jobs_running:

            all_finish = all(self.resource_manager.core_pool[id].state['job_remaining_ops'] == 0
                                   for id in job.allocation)
            if job.is_job_finished():
                finish_jobs.append(job)

        for job in finish_jobs:
            self.scheduler.onJobCompletion(job)
            self.job_scheduler.job_complete(job, self.simulation_time)
            job.allocation = None

    def peek_jobs_now(self) -> None:
        while self.job_scheduler.nb_jobs_queue_left > 0 and \
                self.job_scheduler.show_first_job_in_queue().subtime == self.simulation_time:
            job = self.job_scheduler.pop_first_job_in_queue()
            self.scheduler.onJobSubmission(job)
            self.job_scheduler.new_job(job)

    def schedule_jobs(self) -> None:

        scheduled_jobs = []
        serviceable = True
        while self.job_scheduler.nb_pending_jobs > 0 and serviceable:
            job = self.job_scheduler.peek_job()
            # Pass the current timestamp for registering job entrance in the resource
            resources = self.resource_manager.get_resources(job, self.simulation_time)
            if not resources:
                serviceable = False

            else:
                job.allocation = resources
                scheduled_jobs.append(job)
                self.job_scheduler.remove_job()
        # Execute the jobs if they exist
        if scheduled_jobs:
            self.job_scheduler.nb_active_jobs += len(scheduled_jobs)
            self.job_scheduler.run_jobs(scheduled_jobs, self.simulation_time)

    def calculate_next_scheduler_step(self) -> float:
        time_finish_one_core = float("inf")
        for job in self.job_scheduler.jobs_running:

            time_finish_core_job = min([math.ceil(self.resource_manager.core_pool[id].state['job_remaining_ops'] / \
                                self.resource_manager.core_pool[id].state['current_gflops'] * 1e9)/1e9
                                for id in job.allocation
                                if self.resource_manager.core_pool[id].state['job_remaining_ops'] != 0])

            if time_finish_one_core > time_finish_core_job:
                time_finish_one_core = time_finish_core_job


        if self.job_scheduler.nb_jobs_queue_left > 0:
            time_min_job_start = self.job_scheduler.show_first_job_in_queue().subtime
            if time_min_job_start <= self.simulation_time + time_finish_one_core:
                return time_min_job_start
        return self.simulation_time + time_finish_one_core




    def total_nodes_platform(self) -> int:
        return self.resource_manager.platform['total_nodes']

    def total_processors_platform(self) -> int:
        return self.resource_manager.platform['total_processors']

    def total_cores_platform(self) -> int:
        return self.resource_manager.platform['total_cores']

    def clusters_platform(self) -> list:
        return self.resource_manager.platform['clusters']

    def pending_jobs(self) -> list:
        return self.job_scheduler.pending_jobs

    def job_limits(self) -> dict:
        return self.resource_manager.platform['job_limits']

    def set_job_sorting_key(self, key):
        self.job_scheduler.sorting_key = key

    def set_resource_sorting_key(self, key):
        self.resource_manager.sorting_key = key

    def get_energy_last_period(self) -> float:
        return self.statistics.energy[-1]

    def get_edp_last_period(self) -> float:
        return self.statistics.edp[-1]

    def get_final_edp(self) -> float:
        return sum(self.statistics.latest_edp)

    def get_final_energy(self) -> float:
        return sum(self.statistics.latest_energy)

    def no_more_static_jobs(self) -> bool:
        return len(self.job_scheduler.jobs_running) > 0
