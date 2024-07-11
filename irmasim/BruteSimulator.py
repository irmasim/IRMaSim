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
        memo = {}
        return { "simulator": deepcopy(self, memo) }

    def restore(self, checkpoint):
        self.__dict__.update(checkpoint["simulator"].__dict__)
        self.workload_manager.simulator = self
        return self

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

        while not end:
            simulator_handler.setFormatter(logging.Formatter(f'{branch},%(message)s'))
            self.log_state()
            parent = self.simulation_time
            end = self.simulate_step()
            if end:
                if stack:
                    print(f"Branch: {branch}")
                    self.simulation_summary_branch(branch)
                    checkpoint = stack.pop()
                    self.restore(checkpoint)
                    branch = checkpoint["branch"]
                    choice = checkpoint["choice"]
                    print(f"Backtracking {branch}")
                    self.workload_manager.schedule_choice(choice)
                    end = False

            if not end:
                while True:
                    choices = self.workload_manager.get_choices()
                    if not choices:
                        break
                    for choice in choices[1:]:
                        checkpoint = self.checkpoint()
                        checkpoint["branch"] = branches
                        checkpoint["choice"] = choice
                        stack.append(checkpoint)
                        print(f"Branching {branches}")
                        branches += 1
                    choice = choices[0]
                    self.workload_manager.schedule_choice(choice)

        print(f"End of branch {branch}")
        self.simulation_summary_branch(branch)
        simulator_handler.setFormatter(logging.Formatter(f'{branch},%(message)s'))
        self.log_state()

    def __str__(self):
        parent = super().__str__()
        return parent + f" job_log: {len(self.job_log)}"
