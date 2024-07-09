from copy import deepcopy
from irmasim.Simulator import Simulator
import logging
import math

class BruteSimulator(Simulator):

    def __init__(self):
        super().__init__()
        self.job_log = []
        self.job_logger = logging.getLogger("jobs")
        job_handler = logging.getLogger("jobs").handlers[0]

    def checkpoint(self):
        ret = {
            "simulation_time": self.simulation_time,
            "energy": self.energy,
            "job_queue": deepcopy(self.job_queue),
            "platform": deepcopy(self.platform),
        }
        self.workload_manager.simulator = None
        ret["workload_manager"] = deepcopy(self.workload_manager)
        self.workload_manager.simulator = self
        return ret

    def restore(self, checkpoint):
        self.simulation_time = checkpoint["simulation_time"]
        self.energy = checkpoint["energy"]
        self.job_queue = checkpoint["job_queue"]
        self.platform = checkpoint["platform"]
        self.workload_manager = checkpoint["workload_manager"]
        self.workload_manager.simulator = self

    def simulation_summary_branch(self, branch):
        self.simulation_summary()
        self.job_logger.handlers[0].setFormatter(logging.Formatter(f'{branch},%(message)s'))
        [ self.job_logger.info(task_str) for task_str in self.job_log ]

    def simulate_step(self):
        delta_time_platform = self.platform.get_next_step()
        delta_time_queue = self.job_queue.get_next_step() - self.simulation_time
        delta_time = min([delta_time_platform, delta_time_queue])

        if delta_time == math.inf:
            return True

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
                self.job_log.extend(job.task_strs())
                self.energy_user_estimation += job.req_energy * job.ntasks
            self.reap([task for job in jobs for task in job.tasks])
            self.workload_manager.on_job_completion(jobs)

        return False

    def simulate_trajectory(self) -> None:
        simulator_handler = logging.getLogger("simulator").handlers[0]
        logging.getLogger("irmasim").debug("Simulation start")
        branch = 0
        branches = 1
        stack = []
        end = False
        simulator_handler.setFormatter(logging.Formatter(f'{branch},%(message)s'))
        self.log_state()

        while not end:
            parent = self.simulation_time
            end = self.simulate_step()
            choice = None
            if not end:
                choices = self.workload_manager.get_choices()
                checkpoint = None
                for choice in choices[1:]:
                    checkpoint = self.checkpoint() if checkpoint is None else checkpoint
                    checkpoint["branch"] = branches
                    checkpoint["choice"] = choice
                    stack.append(checkpoint)
                    branches += 1
                choice = choices[0] if choices else None
            else:
                if stack:
                    print(f"Branch: {branch}")
                    self.simulation_summary_branch(branch)
                    print("Backtracking")
                    checkpoint = stack.pop()
                    self.restore(checkpoint)
                    branch = checkpoint["branch"]
                    choice = checkpoint["choice"]
                    end = False

            if choice is not None:
                self.workload_manager.schedule_choice(choice)
            simulator_handler.setFormatter(logging.Formatter(f'{branch},%(message)s'))
            self.log_state()
        print(f"Branch: {branch}")
        self.simulation_summary_branch(branch)

