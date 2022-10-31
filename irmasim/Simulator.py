import math
from irmasim.Job import Job
from irmasim.JobQueue import JobQueue
from irmasim.workload_manager.Basic import Basic
from irmasim.Options import Options
import importlib
import os.path as path
import json
import numpy
import logging


class Simulator:

    def __init__(self):
        self.job_limits, self.job_queue = self.generate_workload()
        self.platform = self.build_platform()
        print(self.platform.pstr("  "))
        self.workload_manager = self.build_workload_manager()
        # TODO
        # self.statistics = Statistics(options)
        self.simulation_time = 0
        self.energy = 0
        self.logger = logging.getLogger("simulator")
        self.logger.info("time,energy,future_jobs,pending_jobs,running_jobs,finished_jobs")

    def start_simulation(self) -> None:
        self.log_state()
        first_jobs = self.job_queue.get_next_jobs(self.job_queue.get_next_step())
        self.simulation_time += first_jobs[0].submit_time
        self.platform.advance(self.simulation_time)
        # TODO do something with joules
        self.energy = self.platform.get_joules(self.simulation_time)
        # self.statistics.calculate_energy_and_edp(self.resource_manager.core_pool, self.simulation_time)
        self.workload_manager.on_job_submission(first_jobs)
        self.log_state()

        delta_time_platform = self.platform.get_next_step()
        # TODO unify get_next_step return value
        delta_time_queue = self.job_queue.get_next_step() - self.simulation_time

        delta_time = min([delta_time_platform, delta_time_queue])

        while delta_time != math.inf:
            if delta_time != 0:

                print("delta", delta_time)
                self.platform.advance(delta_time)
                print("ENE", self.platform.get_joules(delta_time))
                self.energy += self.platform.get_joules(delta_time)
                self.simulation_time += delta_time

            if delta_time == delta_time_queue:
                jobs = self.job_queue.get_next_jobs(self.simulation_time)
                self.workload_manager.on_job_submission(jobs)

            if delta_time == delta_time_platform:
                jobs = self.job_queue.finish_jobs()
                job_logger = logging.getLogger("jobs")
                for job in jobs:
                    job.finish_time = self.simulation_time
                    job_logger.info(str(job))
                self.reap([task for job in jobs for task in job.tasks])
                self.workload_manager.on_job_completion(jobs)

            if delta_time == delta_time_queue or delta_time == delta_time_platform:
                self.workload_manager.on_end_step()


            delta_time_platform = self.platform.get_next_step()
            # TODO unify get_next_step return value
            delta_time_queue = self.job_queue.get_next_step() - self.simulation_time
            delta_time = min([delta_time_platform, delta_time_queue])
            self.log_state()
        self.workload_manager.on_end_simulation()

    def schedule(self, tasks: list):
        for task in tasks:
            task.job.set_start_time(self.simulation_time)
            resource_id = task.resource[0]
            if resource_id == self.platform.id:
                self.platform.schedule(task, task.resource[1:])

    def reap(self, tasks: list):
        for task in tasks:
            resource_id = task.resource[0]
            if resource_id == self.platform.id:
                self.platform.reap(task, task.resource[1:])

    def get_next_step(self) -> float:
        return min([self.platform.get_next_step(), self.job_queue.get_next_step()])

    def get_resources_ids(self):
        return self.platform.enumerate_ids()

    def get_resources(self, resource_type: type):
        return self.platform.enumerate_resources(resource_type)

    def build_platform(self):
        options = Options().get()
        library = self._build_library(options.get('platform_file'), options['platform_library_path'])
        platform_description = library['platform'][options['platform_name']]
        print(f'Using platform {options["platform_name"]}')
        options["platform_model_name"] = platform_description["model_name"]
        mod = importlib.import_module("irmasim.platform.models."+platform_description["model_name"]+".ModelBuilder")
        klass = getattr(mod, 'ModelBuilder')
        model_builder = klass(platform_description=platform_description, library=library)
        return model_builder.build_platform()

    def _build_library(self, platform_file_path: str, platform_library_path: str) -> dict:
        types = {}
        for pair in [('platform', 'platforms.json'), ('network', 'network_types.json'), ('node', 'node_types.json'),
                     ('processor', 'processor_types.json')]:
            types[pair[0]] = {}
            lib_filename = path.join(platform_library_path, pair[1])
            if path.isfile(lib_filename):
                with open(lib_filename, 'r') as lib_f:
                    print(f'Loading definitions from {lib_filename}')
                    types.update({pair[0]: json.load(lib_f)})

        if platform_file_path:
            with open(platform_file_path, 'r') as in_f:
                print(f'Loading definitions from {platform_file_path}')
                types_from_file = json.load(in_f)
                for group in types_from_file:
                    types[group].update(types_from_file[group])
        return types

    def generate_workload(self):
        options = Options().get()
        with open(options['workload_file'], 'r') as in_f:
            workload = json.load(in_f)

        job_queue = JobQueue()
        job_id = 0
        for job in workload['jobs']:
            job_queue.add_job(
                Job(job_id, job['id'], job['subtime'], job['res'], workload['profiles'][job['profile']],
                    job['profile']))
            job_id = job_id + 1

        job_limits = {
            'max_time': numpy.percentile(numpy.array(
                [workload['profiles'][job['profile']]['req_time'] for job in workload['jobs']]), 99),
            'max_core': numpy.percentile(numpy.array(
                [job['res'] for job in workload['jobs']]), 99),
            'max_mem': numpy.percentile(numpy.array(
                [workload['profiles'][job['profile']]['mem'] for job in workload['jobs']]), 99),
            'max_mem_vol': numpy.percentile(numpy.array(
                [workload['profiles'][job['profile']]['mem_vol'] for job in workload['jobs']]), 99)
        }
        return job_limits, job_queue

    def build_workload_manager(self):
        options = Options().get()
        mod = importlib.import_module("irmasim.workload_manager." + options["workload_manager"]["type"])
        klass = getattr(mod, options["workload_manager"]["type"])
        return klass(self)

    def log_state(self):
        future, pending, running, finished = self.job_queue.get_job_counts()
        self.logger.info(",".join(map(lambda x: str(x), [self.simulation_time, self.energy, future, pending, running, finished])))
