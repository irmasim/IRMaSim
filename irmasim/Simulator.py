import math
from irmasim.Job import Job
from irmasim.JobQueue import JobQueue
from irmasim.workload_manager.WorkloadManager import WorkloadManager
from irmasim.Options import Options
import importlib
import os.path as path
import json
import numpy
import logging
import random as rand


class Simulator:

    def __init__(self):
        self.platform = self.build_platform()
        #print(self.platform.pstr("  "))
        self.workload = None
        self.workload_manager = self.build_workload_manager()
        # TODO
        # self.statistics = Statistics(options)
        self.simulation_time = 0
        self.energy = 0
        self.logger = logging.getLogger("simulator")

        self.resource_logger = None
        options = Options().get()
        if 'log_resource_type' in options:
            print(f"Logging resources of type {options['log_resource_type']}")
            mod = importlib.import_module('irmasim.platform.models.' + options['platform_model_name'] + \
                    '.' + options['log_resource_type'])
            klass = getattr(mod, options['log_resource_type'])
            self.log_resources = self.get_resources(klass)
            self.resource_logger = logging.getLogger("resources")
            self.resource_logger.info("time," + klass.header())

    def start_simulation(self) -> None:
        options = Options().get()
        nbtrajectories = int(options['nbtrajectories'])
        for i in range(nbtrajectories):
            self.simulation_time = 0
            self.job_queue = self.generate_workload(self.simulation_time)
            self.simulate_trajectory()
            self.workload_manager.on_end_trajectory()
        self.workload_manager.on_end_simulation()

    def simulate_trajectory(self) -> None:
        logging.getLogger("irmasim").debug("Simulation start")
        self.log_state()
        first_jobs = self.job_queue.get_next_jobs(self.job_queue.get_next_step())
        self.simulation_time += first_jobs[0].submit_time
        self.platform.advance(self.simulation_time)
        # TODO do something with joules
        self.energy = self.platform.get_joules(self.simulation_time)
        # self.statistics.calculate_energy_and_edp(self.resource_manager.core_pool, self.simulation_time)
        logging.getLogger("irmasim").debug("{} Received job submission: {}".format( \
                self.simulation_time, ",".join([str(job.id)+"("+job.name+")" for job in first_jobs])))
        self.workload_manager.on_job_submission(first_jobs)
        self.workload_manager.on_end_step()
        
        self.log_state()

        delta_time_platform = self.platform.get_next_step()
        # TODO unify get_next_step return value
        delta_time_queue = self.job_queue.get_next_step() - self.simulation_time

        delta_time = min([delta_time_platform, delta_time_queue])

        while delta_time != math.inf:
            if delta_time != 0:
                self.platform.advance(delta_time)
                self.energy += self.platform.get_joules(delta_time)
                self.simulation_time += delta_time

            if delta_time == delta_time_queue:
                jobs = self.job_queue.get_next_jobs(self.simulation_time)
                logging.getLogger("irmasim").debug("{} Received job submission: {}".format( \
                        self.simulation_time, ",".join([str(job.id)+"("+job.name+")" for job in jobs])))
                self.workload_manager.on_job_submission(jobs)

            if delta_time == delta_time_platform:
                jobs = self.job_queue.finish_jobs()
                job_logger = logging.getLogger("jobs")
                for job in jobs:
                    job.finish_time = self.simulation_time
                    [ job_logger.info(task_str) for task_str in job.task_strs() ]
                self.reap([task for job in jobs for task in job.tasks])
                self.workload_manager.on_job_completion(jobs)

            if delta_time == delta_time_queue or delta_time == delta_time_platform:
                self.workload_manager.on_end_step()

            delta_time_platform = self.platform.get_next_step()
            # TODO unify get_next_step return value
            delta_time_queue = self.job_queue.get_next_step() - self.simulation_time
            delta_time = min([delta_time_platform, delta_time_queue])
            self.log_state()

    def schedule(self, tasks: list):
        for task in tasks:
            task.job.set_start_time(self.simulation_time)
            resource_id = task.resource[0]
            if resource_id == self.platform.id:
                logging.getLogger("irmasim").debug("{} {} launch task {} runs task {}".format( \
                        self.simulation_time, ".".join(task.resource), task.job.name, task.job.type))
                self.platform.schedule(task, task.resource[1:])
            else:
                raise Exception(f"Resource {task.resource} does not belong to platform {self.platform.id}")

    def reap(self, tasks: list):
        for task in tasks:
            resource_id = task.resource[0]
            if resource_id == self.platform.id:
                logging.getLogger("irmasim").debug("{} {} complete task {}".format( \
                        self.simulation_time, ".".join(task.resource), task.job.name))
                self.platform.reap(task, task.resource[1:])

    def get_next_step(self) -> float:
        return min([self.platform.get_next_step(), self.job_queue.get_next_step()])

    def get_resources_ids(self):
        return self.platform.enumerate_ids()

    def get_resources(self, resource_type: type):
        return self.platform.enumerate_resources(resource_type)
    
    def get_resource(self, resource_id: list):
        if resource_id.pop(0) == self.platform.id:
            return self.platform.get_resource(resource_id)
        else:
            raise Exception(f"Resource {'.'.join(resource_id)} does not belong to platform {self.platform.id}")

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

    def get_workload_limits(self):
        def ntasks(job: dict):
            if 'res' in job:
                return job['res']
            else:
                return job['ntasks']

        def from_profile(key: str, job: dict, workload: dict):
            if 'profile' in job:
                return workload['profiles'][job['profile']][key]
            else:
                return job[key]

        self.load_workload()

        job_limits = {
            'max_time': numpy.percentile(numpy.array(
                [from_profile('req_time',job,self.workload) for job in self.workload['jobs']]), 99),
            'max_core': numpy.percentile(numpy.array(
                #TODO: Repensar en relacion a ntasks y ntasks-per-node. A lo mejor deberia llamarse max_tasks
                [ntasks(job) for job in self.workload['jobs']]), 99),
            'max_mem': numpy.percentile(numpy.array(
                [from_profile('mem',job,self.workload) for job in self.workload['jobs']]), 99),
            'max_mem_vol': numpy.percentile(numpy.array(
                [from_profile('mem_vol',job,self.workload) for job in self.workload['jobs']]), 99)
        }

        return job_limits

    def load_workload(self):
        options = Options().get()
        if self.workload == None:
            with open(options['workload_file'], 'r') as in_f:
                self.workload = json.load(in_f)
            print(f'Loaded {len(self.workload["jobs"])} jobs from {options["workload_file"]}')

    def generate_workload(self, simulation_time:float = 0.0):
        self.load_workload()
        options = Options().get()
        if options['trajectory_length'] == 'random':
            trajectory_length = rand.randint(1, len(self.workload['jobs']))
        else:
            trajectory_length = int(options['trajectory_length'])

        if options['trajectory_origin'] == 'random':
            l=trajectory_length
            if l == 0:
                l = 1
            trajectory_origin = rand.randint(0, len(self.workload['jobs'])-l)
        else:
            trajectory_origin = int(options['trajectory_origin'])
        if trajectory_length == 0:
            trajectory_length = len(self.workload['jobs']) - trajectory_origin

        print(f'Using {trajectory_length} jobs starting with #{trajectory_origin}')
        
        job_queue = JobQueue()
        job_id = trajectory_origin
        first_job_subtime = self.workload['jobs'][trajectory_origin]['subtime']
        for i in range(trajectory_length):
            job = self.workload['jobs'][trajectory_origin+i]
            if 'id' not in job:
                job['id'] = "job"+str(job_id)
            if 'res' in job:
                if 'nodes' in job or 'ntasks' in job or 'ntasks_per_node' in job:
                    raise Exception(f"A job can specify a 'res' option or ('nodes','ntasks','ntasks_per_node'). But Job {job['id']} specify both")
                job['nodes'] = 1
                job['ntasks'] = job['res']
                del job['res']
            if 'ntasks' not in job and 'nodes' not in job:
                raise Exception(f"Job {job['id']} requires specifying 'nodes' or 'ntasks' at least")
            if 'ntasks' in job and 'nodes' in job and 'ntasks_per_node' in job:
                if job['nodes'] != math.ceil(job['ntasks'] / job['ntasks_per_node']):
                    raise Exception(f"Job {job['id']} has incompatible values of 'nodes', 'ntasks' and 'ntasks_per_node'")
            if 'nodes' not in job:
                if 'ntasks_per_node' not in job:
                   job['ntasks_per_node'] = 1
                job['nodes'] = math.ceil(job['ntasks'] / job['ntasks_per_node'])
            else:
                if 'ntasks' not in job:
                    if 'ntasks_per_node' not in job:
                        job['ntasks_per_node'] = 1
                    job['ntasks'] = job['nodes'] * job['ntasks_per_node']
                else:
                    job['ntasks_per_node'] = math.ceil(job['ntasks']/job['nodes'])
            if 'profile' in job:
                job_queue.add_job(
                Job.from_profile(job_id, job['id'], job['subtime']-first_job_subtime + simulation_time, job['nodes'], job['ntasks'], job['ntasks_per_node'],
                    self.workload['profiles'][job['profile']], job['profile']))
            else:
                job_queue.add_job(
                Job(job_id, job['id'], job['subtime']-first_job_subtime + simulation_time, job['nodes'], job['ntasks'], job['ntasks_per_node'],
                    job['req_ops'], job['ipc'], job['req_time'], job['mem'], job['mem_vol']))
            job_id += 1

        return job_queue

    def build_workload_manager(self):
        options = Options().get()
        module_name = "irmasim.workload_manager." + options["workload_manager"]["type"]
        print(f'Using workload manager {module_name}')
        mod = importlib.import_module(module_name)
        klass = getattr(mod, options["workload_manager"]["type"])
        return klass(self)

    def log_state(self):
        state = [ self.simulation_time, self.energy ]
        state.extend(self.job_queue.get_job_counts())

        for stats in [ self.slowdown_statistics(),
                       self.bounded_slowdown_statistics(),
                       self.waiting_time_statistics() ]:
           state.extend(stats.values())

        self.logger.info(",".join(map(lambda x: str(x), state)))

        if self.resource_logger != None:
            for resource in self.log_resources:
                self.resource_logger.info(str(self.simulation_time) + "," + resource.log_state())

    def slowdown_statistics(self) -> dict:
        sld_list = []
        for job in self.job_queue.finished_jobs:
            if job.finish_time - job.start_time == 0:
                print(f"warning: {job.id} has 0 execution time")
            sld_list.append(float(job.finish_time - job.submit_time) / (job.finish_time - job.start_time))

        return self.compute_statistics(sld_list)

    def bounded_slowdown_statistics(self) -> dict:
        bsld_list = []
        for job in self.job_queue.finished_jobs:
            bsld_list.append( max(float(job.finish_time - job.submit_time)/max(job.finish_time - job.start_time,10), 1) )

        return self.compute_statistics(bsld_list)
    
    def waiting_time_statistics(self) -> dict:
        waiting_time_list = []
        for job in self.job_queue.finished_jobs:
            waiting_time_list.append(float(job.start_time - job.submit_time))
        
        return self.compute_statistics(waiting_time_list)

    def energy_consumption_statistics(self) -> dict:
        return {"total": self.energy}

    def simulation_time_statistics(self) -> dict:
        return {"total": self.simulation_time}

    def job_statistics(self) -> dict:
        counts = self.job_queue.get_job_counts()
        return {"future": counts[0], "queue": counts[1], "running": counts[2], "finished": counts[3]}

    def compute_statistics(self, statistic_list) -> dict:
        total = 0.0
        avg = 0.0
        max = float(-math.inf)
        min = float(math.inf)

        for stat in statistic_list:
            total += stat
            if (stat > max):
                max = stat
            if (stat < min):
                min = stat
        try:
            avg = total/len(statistic_list)
        except:
            avg = total/1

        return {"total": total, "avg": avg, "max": max, "min": min}

    @classmethod
    def header(klass):
        header = "time,energy,future_jobs,pending_jobs,running_jobs,finished_jobs"
        for metric in [ "slowdown", "bounded_slowdown", "waiting_time" ]:
           header += "," + ",".join([metric+"_"+stat for stat in ["total","avg","max","min"]])
        return header
