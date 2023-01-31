import importlib
import torch
import logging
import os.path as path

from irmasim.Options import Options
from irmasim.workload_manager.ActionEnvironment import ActionEnvironment
from irmasim.workload_manager.Policy import Policy
from irmasim.workload_manager.WorkloadManager import WorkloadManager
from irmasim.workload_manager.agent.ActionActorCritic import ActionActorCritic
from irmasim.workload_manager.agent.ActionActorCritic import PPOTrainer

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from irmasim.Simulator import Simulator

options = Options().get()
mod = importlib.import_module("irmasim.platform.models." + options["platform_model_name"] + ".Core")
core_klass = getattr(mod, 'Core')

class Action(Policy):

    def __init__(self, simulator: 'Simulator'):
        WorkloadManager.__init__(self, simulator)
        if simulator.platform.config["model"] != "modelV1":
            raise Exception("Policy workload manager needs a modelV1 platform")
        options = Options().get()
        mod = importlib.import_module("irmasim.platform.models." + options["platform_model_name"] + ".Node")
        klass = getattr(mod, 'Node')
        self.resources = self.simulator.get_resources(klass)
        self.pending_jobs = []
        self.running_jobs = []
        self.load_agent = True
        self.last_reward = False
        self.reward = options["workload_manager"]["environment"]["objective"]
        self.last_time = 0

        self.environment = ActionEnvironment(self, simulator)
        self.agent, self.optimizers = self.create_agent()
        self.ppo_trainer = PPOTrainer(self.agent, self.optimizers.optimizer_pi, self.optimizers.optimizer_v)

    def create_agent(self):
        agent_options = Options().get()["workload_manager"]["agent"]
        agent = ActionActorCritic(self.environment.action_size, self.environment.observation_size)
        optimizer_pi: torch.optim = torch.optim.Adam(agent.actor.parameters(), lr=float(agent_options['lr_pi']))
        optimizer_v: torch.optim = torch.optim.Adam(agent.critic.parameters(), lr=float(agent_options['lr_v']))
        optimizers = MultiOptimWrapper(optimizer_pi, optimizer_v)

        if 'input_model' in agent_options and path.isfile(agent_options['input_model']) and self.load_agent:
            print(f"Reading model to {agent_options['input_model']}")
            checkpoint = torch.load(agent_options['input_model'])
            agent.load_state_dict(checkpoint['model_state_dict'])
            checkpoint['optimizer_state_dict']['pi']['param_groups'][0]['lr'] = float(agent_options['lr_pi'])
            checkpoint['optimizer_state_dict']['v']['param_groups'][0]['lr'] = float(agent_options['lr_v'])
            optimizers.load_state_dict(checkpoint['optimizer_state_dict'])
        agent.train() if agent_options['phase'] == 'train' else agent.eval()
        return agent, optimizers

    def on_end_step(self):
        if self.pending_jobs and any(self._is_schedulable(job) for job in self.pending_jobs[:self.environment.NUM_JOBS]):
            self.last_time = self.simulator.simulation_time
            observation = self.agent.observe(self.environment)
            action, v, logp = self.agent.decide(torch.as_tensor(observation, dtype=torch.float32))
            self.apply_action(action)
            self.agent.store_values(observation, action, 0, v, logp)

    def _is_schedulable(self, job):
        return job.ntasks <= max([node.count_idle_cores() for node in self.resources])

    def apply_action(self, action: int):
        job_idx, node_idx = self.environment.get_action_pair(action)
        logging.getLogger("irmasim").debug(
            f"{self.simulator.simulation_time} performing action Job({job_idx})-Node({node_idx}) ({action})")
        job, node = self.pending_jobs.pop(job_idx), self.resources[node_idx]

        free_cores = [core for core in node.enumerate_resources(core_klass) if core.task is None]
        assert len(free_cores) >= job.ntasks
        for task in job.tasks:
            task.allocate(free_cores.pop(0).full_id())
        self.simulator.schedule(job.tasks)
        self.running_jobs.append(job)
        slowdown = float(job.start_time) - float(job.submit_time)
        logging.getLogger("irmasim").debug(f'{self.simulator.simulation_time} {job.name} was scheduled with a slowdown of {slowdown}')

    def on_end_trajectory(self):
        logging.getLogger('irmasim').debug(f'{self.simulator.simulation_time} - Ending trajectory')
        self.agent.finish_trajectory(self.environment.reward())

    def on_end_simulation(self):
        options = Options().get()
        if options['workload_manager']['agent']['phase'] == 'train':
            losses = self.ppo_trainer.update()
            with open('{0}/losses.log'.format(options['output_dir']), 'a+') as out_f:
                out_f.write(f'{losses[0]},{losses[1]}\n')
            if 'output_model' in options['workload_manager']['agent']:
                print(f"Writing model to {options['workload_manager']['agent']['output_model']}")
                torch.save({
                    'model_state_dict': self.agent.state_dict(),
                    'optimizer_state_dict': self.optimizers.state_dict()
                }, options['workload_manager']['agent']['output_model'])
        with open('{0}/rewards.log'.format(options['output_dir']), 'a+') as out_f:
            out_f.write(f'{self.agent.total_rewards}\n')


class MultiOptimWrapper:

    def __init__(self, optimizer_pi: torch.optim, optimizer_v: torch.optim):
        self.optimizer_pi = optimizer_pi
        self.optimizer_v = optimizer_v

    def state_dict(self):
        return {
            'pi': self.optimizer_pi.state_dict(),
            'v': self.optimizer_v.state_dict()
        }

    def load_state_dict(self, state_dict: dict):
        self.optimizer_pi.load_state_dict(state_dict['pi'])
        self.optimizer_v.load_state_dict(state_dict['v'])
