import importlib
import json
import numpy as np
import torch
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
        self.load_agent = True
        self.last_reward = False
        # if objective change reset agent
        self.reward = options["workload_manager"]["env"]["objective"]
        self.last_time = 0
        # TODO analyse the need for this function
        # self.reset_log_file(options)

        self.env = Environment(self, simulator)
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
                reset.write(options["env"]['objective'])
        except OSError as err:
            logging.error("{0}".format(err))
            raise
        except IOError:
            logging.error("Error writing to {0}".format(reset_log_file))
            raise
    """

    def create_agent(self):
        agent_options = Options().get()["workload_manager"]["agent"]
        mod = importlib.import_module("irmasim.workload_manager.agent." + agent_options["name"])
        klass = getattr(mod, agent_options["name"])
        agent = klass(self.env.action_size, self.env.observation_size)
        optimizer: torch.optim = torch.optim.Adam(agent.parameters(), lr=float(agent_options['lr']))

        if 'input_model' in agent_options and path.isfile(agent_options['input_model']) and self.load_agent:
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
            self.running_jobs.remove(job)

    def on_end_step(self):
        self.agent.rewarded(self.env)
        self.last_time = self.simulator.simulation_time
        observation = self.agent.observe(self.env)
        action = self.agent.decide(observation)
        self.apply_policy(action)

    def apply_policy(self, action: int):
        print(self.env.actions)
        print(action)
        key = self.env.actions[action]
        self.pending_jobs.sort(key=key[0])
        available_resources = [resource for resource in self.resources if resource.task is None]
        print(key[1])
        available_resources.sort(key=key[1])
        while self.pending_jobs and len(self.pending_jobs[0].tasks) >= len(available_resources):
            next_job = self.pending_jobs.pop(0)
            for task in next_job.tasks:
                task.allocate(available_resources.pop(0).id)
            self.simulator.schedule(next_job.tasks)
            self.running_jobs.append(next_job)

    def on_end_simulation(self):
        options = Options().get()
        if options["workload_manager"]['agent']['phase'] == 'train':
            loss = self.agent.loss()
            with open('{0}/losses.log'.format(options['output_dir']), 'a+') as out_f:
                out_f.write(f'{loss}\n')
            self.optimizer.zero_grad()
            loss.backward()
            self.optimizer.step()
            if 'output_model' in options["workload_manager"]['agent']:
                torch.save({
                    'model_state_dict': self.agent.state_dict(),
                    'optimizer_state_dict': self.optimizer.state_dict()
                }, options["workload_manager"]['output_model'])
        with open('{0}/rewards.log'.format(options['output_dir']), 'a+') as out_f:
            out_f.write(f'{np.sum(self.agent.rewards)}\n')
        with open('{0}/makespans.log'.format(options['output_dir']), 'a+') as out_f:
            out_f.write(f'{self.simulator.simulation_time}\n')
        if hasattr(self.agent, 'probs'):
            if path.isfile('{0}/probs.json'.format(options['output_dir'])):
                with open('{0}/probs.json'.format(options['output_dir']), 'r') as in_f:
                    probs = json.load(in_f)['probs']
                for action, prob in zip(range(self.env.action_size), self.agent.probs):
                    probs[action].append(prob)
            else:
                probs = []
                for prob in self.agent.probs:
                    probs.append([prob])
            with open('{0}/probs.json'.format(options['output_dir']), 'w+') as out_f:
                json.dump({'probs': probs}, out_f, indent=4)
