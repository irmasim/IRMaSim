import importlib
import json
import numpy as np
import torch
import logging
import os.path as path
from irmasim.workload_manager.WorkloadManager import WorkloadManager
from irmasim.Options import Options
from irmasim.workload_manager.Environment import Environment
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from irmasim.Simulator import Simulator


class Policy(WorkloadManager):
    def __init__(self, simulator: 'Simulator'):
        super(Policy, self).__init__(simulator)
        if simulator.platform.config["model"] != "modelV1":
            raise Exception("Policy workload manager needs a modelV1 platform")
        options = Options().get()
        mod = importlib.import_module("irmasim.platform.models." + options["platform_model_name"] + ".Core")
        klass = getattr(mod, 'Core')
        self.resources = self.simulator.get_resources(klass)
        self.pending_jobs = []
        self.running_jobs = []
        self.load_agent = True
        self.last_reward = False
        # if objective change reset agent
        self.reward = options["workload_manager"]["environment"]["objective"]
        self.last_time = 0
        # TODO analyse the need for this function
        # self.reset_log_file(options)

        self.environment = Environment(self, simulator)
        self.agent, self.optimizer = self.create_agent()
        self.flow_flags = {
            'action_taken': False,
            'void_taken': False
        }

    """
    def reset_log_file(self, options):
        reset_log_file = "%s/reset.log" % (options['output_dir'])
        try:
            with open(reset_log_file, 'r') as reset:
                lines = reset.read()
                logging.debug(lines)
                if lines != self.reward:
                    self.load_agent = False
        except OSError:
            logging.info("Could not open {0} for reading".format(reset_log_file))
        except IOError:
            logging.error("Error reading from {0}".format(reset_log_file))
        try:
            with open(reset_log_file, 'w') as reset:
                reset.write(options["environment"]['objective'])
        except OSError as err:
            logging.error("{0}".format(err))
            raise
        except IOError:
            logging.error("Error writing to {0}".format(reset_log_file))
            raise
    """

    def create_agent(self):
        agent_options = Options().get()["workload_manager"]["agent"]
        module = "irmasim.workload_manager.agent." + agent_options["name"]
        print(f"Using agent {module}.")
        mod = importlib.import_module(module)
        klass = getattr(mod, agent_options["name"])
        agent = klass(self.environment.action_size, self.environment.observation_size)
        optimizer: torch.optim = torch.optim.Adam(agent.parameters(), lr=float(agent_options['lr']))

        if 'input_model' in agent_options and path.isfile(agent_options['input_model']) and self.load_agent:
            print(f"Reading model to {agent_options['input_model']}")
            checkpoint = torch.load(agent_options['input_model'])
            agent.load_state_dict(checkpoint['model_state_dict'])
            checkpoint['optimizer_state_dict']['param_groups'][0]['lr'] = float(agent_options['lr'])
            optimizer.load_state_dict(checkpoint['optimizer_state_dict'])

        if agent_options['phase'] == 'train':
            agent.train()
        else:
            agent.eval()
        return agent, optimizer

    def on_job_submission(self, jobs: list):
        self.pending_jobs.extend(jobs)

    def on_job_completion(self, jobs: list):
        for job in jobs:
            logging.getLogger("irmasim").debug(
                f"{self.simulator.simulation_time} {job.name} finished")
            self.running_jobs.remove(job)

    def on_end_step(self):
        self.agent.rewarded(self.environment)
        self.last_time = self.simulator.simulation_time
        observation = self.agent.observe(self.environment)
        action = self.agent.decide(observation)
        self.apply_policy(action)

    def apply_policy(self, action: int):
        key = self.environment.actions[action]
        logging.getLogger("irmasim").debug("{} performing action {}-{} ({})".format( \
                self.simulator.simulation_time, key[2], key[3], action))
        self.pending_jobs.sort(key=key[0])
        available_resources = [resource for resource in self.resources if resource.task is None]
        if key[1] != None:
            available_resources.sort(key=key[1])
        while self.pending_jobs and len(self.pending_jobs[0].tasks) <= len(available_resources):
            next_job = self.pending_jobs.pop(0)
            for task in next_job.tasks:
                task.allocate(available_resources.pop(0).full_id())
            self.simulator.schedule(next_job.tasks)
            self.running_jobs.append(next_job)

    def on_end_simulation(self):
        options = Options().get()
        if options['workload_manager']['agent']['phase'] == 'train':
            loss = self.agent.loss()
            with open('{0}/losses.log'.format(options['output_dir']), 'a+') as out_f:
                out_f.write(f'{loss}\n')
            self.optimizer.zero_grad()
            loss.backward()
            self.optimizer.step()
            if 'output_model' in options['workload_manager']['agent']:
                print(f"Writing model to {options['workload_manager']['agent']['output_model']}")
                torch.save({
                    'model_state_dict': self.agent.state_dict(),
                    'optimizer_state_dict': self.optimizer.state_dict()
                }, options['workload_manager']['agent']['output_model'])
        with open('{0}/rewards.log'.format(options['output_dir']), 'a+') as out_f:
            out_f.write(f'{np.sum(self.agent.rewards)}\n')
