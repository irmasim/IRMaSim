"""
The HDeepRM workload manager is able to evaluate deep reinforcement learning policies in the
framework.
"""

import importlib.util as iutil
import inspect
import json
import logging
import random
import datetime
import os.path as path
import numpy as np
import torch
from Job import Job
from agent import Agent, ClassicAgent
from entrypoints.BaseWorkloadManager import BaseWorkloadManager
from environment import Environment


class HDeepRMWorkloadManager(BaseWorkloadManager):
    """Entrypoint for Deep Reinforcement Learning experimentation.

This Workload Manager generates the HDeepRM Environment and provides a reference of it to the Agent,
who is in charge of making the decisions. It also orchestrates the simulation flow by handling
Batsim events and calling the Agent when it is necessary. It extends the
:class:`~hdeeprm.entrypoints.BaseWorkloadManager.BaseWorkloadManager` for basic event handling.

Attributes:
    env (:class:`~hdeeprm.environment.Environment`):
        The Workload Management Environment. The Agent observes and interacts with it.
    agent (:class:`~hdeeprm.agent.Agent`):
        The Agent in charge of making decisions by observing and altering the Environment.
    optimizer (:class:`~torch.optim.Optimizer`):
        Optimizer for updating the Agent's inner model weights at the end of the simulation.
    step (int):
        Current decision step.
    flow_flags (dict):
        Control the event flow. Fields:

          | jobs_submitted (bool) -
            Becomes ``True`` when at least one job has been submitted.
          | jobs_completed (bool) -
            Becomes ``True`` when at least one job has been completed.
          | action_taken (bool):
            Becomes ``True`` when an action has been taken by the Agent. This triggers the reward
              procedure.
          | void_taken (bool):
            Becomes ``True`` when a void action has been selected.
    """

    def __init__(self, options: dict) -> None:

        super().__init__(options)
        self.load_agent = True
        self.last_reward = False

        #if objective change reset agent
        self.reward = options["env"]['objective']
        try:
            with open("reset.log", 'r') as reset:
                lines = reset.read()
                logging.debug(lines)
                if lines != self.reward:
                    self.load_agent = False

        except IOError:
            logging.info("Not found reset.log")

        try:
            with open("reset.log", 'w') as reset:
                reset.write(options["env"]['objective'])
        except IOError:
            logging.info("Not found reset.log")

        self.env = Environment(self, options['env'])
        self.agent, self.optimizer = self.create_agent(options['agent'], options['seed'])
        self.time_last_step = 0
        self.step = 0
        self.flow_flags = {
            'jobs_submitted': False,
            'jobs_completed': False,
            'action_taken': False,
            'void_taken': False
        }


    def create_agent(self, agent_options: dict, seed: int) -> tuple:
        """Generates the Agent based on the agent options.

The agent class is obtained from the user provided file. It is instantiated according to its parent
class. Previously saved models might be loaded if the user indicates so in command line.

Args:
    agent_options (dict): options for the Agent creation. User provided.
    seed (int): random seed for torch library reproducibility when evaluating.

Returns:
    A tuple with the created Agent and the optimizer in case of training.
        """

        optimizer = None
        if agent_options['type'] == 'CLASSIC':
            #Selection of classic policy
            job_policy, core_policy = agent_options["policy_pair"].split('-')
            job_selection = 0
            core_selection = 0
            find_job_selection = False
            find_core_selection = False

            for job_sel in self.env.job_selections.keys():
                if job_sel != job_policy and find_job_selection == False:
                    job_selection = job_selection + 1
                if job_sel == job_policy:
                    find_job_selection = True
            for core_sel in self.env.core_selections.keys():
                if core_sel != core_policy and find_core_selection == False:
                    core_selection = core_selection + 1
                if core_sel == core_policy:
                    find_core_selection = True

            if find_job_selection == False or find_core_selection == False:
                raise ValueError("Error in the policy of Classic agent")

            action = job_selection*len(self.env.job_selections.keys()) + core_selection
            agent = ClassicAgent(action)

        elif agent_options['type'] == 'LEARNING':
            # Obtain the agent class
            agent_module_name = path.splitext(path.basename(agent_options['file']))[0]
            spec = iutil.spec_from_file_location(agent_module_name, agent_options['file'])
            agent_module = iutil.module_from_spec(spec)
            spec.loader.exec_module(agent_module)
            agent_class = [cl for na, cl in inspect.getmembers(agent_module, inspect.isclass)
                           if getattr(cl, '__module__', None) == agent_module_name
                           and issubclass(cl, Agent)][0]
            agent = agent_class(float(agent_options['gamma']), int(agent_options['hidden']),
                                self.env.action_size, self.env.observation_size)

            # Load previously trained model if the user indicated as option
            optimizer : torch.optim = torch.optim.Adam(agent.parameters(), lr=float(agent_options['lr']))
            if 'input_model' in agent_options and path.isfile(agent_options['input_model']) and self.load_agent:
                checkpoint = torch.load(agent_options['input_model'])
                agent.load_state_dict(checkpoint['model_state_dict'])
                checkpoint['optimizer_state_dict']['param_groups'][0]['lr']=float(agent_options['lr'])
                logging.info(checkpoint['optimizer_state_dict']['param_groups'])
                optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
                logging.debug(optimizer.state_dict())

            if agent_options['run'] == 'train':
                agent.train()
            else:
                agent.eval()
        else:
            raise TypeError('Unrecognized agent type')
        return agent, optimizer

    def onSimulationEnds(self) -> None:
        """Handler triggered when the simulation has ended.

Triggered when receiving a
`SIMULATION_ENDS <https://batsim.readthedocs.io/en/latest/protocol.html#simulation-ends>`_ event.
If the Agent evaluated has been in training mode, the loss is calculated to update its inner model
weights. The updated model is saved if the user has indicated so in command line. Rewards are also
logged for observing performance.
        """


        if self.flow_flags['action_taken'] and self.reward != "makespan":
            # The Agent is rewarded
            self.last_reward = True
            self.agent.rewarded(self.env)
            self.time_last_step = self.bs.time()
            self.flow_flags['action_taken'] = False

        super().onSimulationEnds()
        if self.options['agent']['type'] == 'LEARNING' and self.options['agent']['run'] == 'train':
            loss = self.agent.loss()
            logging.info('Loss %s', loss)
            with open('losses.log', 'a+') as out_f:
                out_f.write(f'{loss}\n')
            # Update parameters
            self.optimizer.zero_grad()
            loss.backward()
            self.optimizer.step()
            if 'output_model' in self.options['agent']:
                torch.save({
                    'model_state_dict': self.agent.state_dict(),
                    'optimizer_state_dict': self.optimizer.state_dict()
                }, self.options['agent']['output_model'])
        # Log scheduled metrics
        logging.info('Max scheduled jobs in one step: %s', self.scheduled_step["max"])
        logging.info('Min scheduled jobs in one step: %s', self.scheduled_step["min"])
        logging.info('Average scheduled jobs in one step: %s', self.scheduled_step["total"]\
                                                               / self.scheduled_step["num_steps"])
        # Save metrics
        with open('rewards.log', 'a+') as out_f:
            out_f.write(f'{np.sum(self.agent.rewards)}\n')
        with open('makespans.log', 'a+') as out_f:
            out_f.write(f'{self.bs.time()}\n')
        if hasattr(self.agent, 'probs'):
            if path.isfile('probs.json'):
                with open('probs.json', 'r') as in_f:
                    probs = json.load(in_f)['probs']
                for action, prob in zip(range(self.env.action_size), self.agent.probs):
                    probs[action].append(prob)
            else:
                probs = []
                for prob in self.agent.probs:
                    probs.append([prob])
            with open('probs.json', 'w+') as out_f:
                json.dump({'probs': probs}, out_f)

    def onJobSubmission(self, job: Job) -> None:
        """Set the "jobs_submitted" flag to ``True``.

Further details on this handler on the base
:meth:`~hdeeprm.entrypoints.BaseWorkloadManager.BaseWorkloadManager.onJobSubmission`.
        """

        if self.flow_flags['action_taken'] and self.reward != "makespan":
            # The Agent is rewarded
            self.agent.rewarded(self.env)
            self.time_last_step = self.bs.time()
            self.flow_flags['action_taken'] = False
        super().onJobSubmission(job)
        self.flow_flags['jobs_submitted'] = True

    def onJobCompletion(self, job: Job) -> None:
        """Set the "jobs_completed" flag to ``True``.

Further details on this handler on the base
:meth:`~hdeeprm.entrypoints.BaseWorkloadManager.BaseWorkloadManager.onJobCompletion`.
        """

        if self.flow_flags['action_taken'] and self.reward != "makespan" and (len(self.job_scheduler.pending_jobs) != 0\
                or self.bs.no_more_static_jobs == False):
            logging.debug(f'{len(self.job_scheduler.pending_jobs)}{self.bs.no_more_static_jobs}')
            # The Agent is rewarded
            self.agent.rewarded(self.env)
            self.time_last_step = self.bs.time()
            self.flow_flags['action_taken'] = False
        super().onJobCompletion(job)
        self.flow_flags['jobs_completed'] = True

    def onNoMoreEvents(self) -> None:
        """
When there are no more events in the current time step, the following flow occurs:

1. The Agent observes the Environment, obatining an approximation of the state.
2. The Agent processes this observation through its inner model, and decides which action to take,
3. The Agent alters the Environment based on the selected action.
4. In the next decision step, the Agent will be rewarded for its action.
        """

        if self.bs.running_simulation:
            if self.flow_flags['action_taken'] and self.reward == "makespan":
                # The Agent is rewarded
                self.agent.rewarded(self.env)
                self.flow_flags['action_taken'] = False

            if (self.flow_flags['jobs_submitted'] or self.flow_flags['jobs_completed'] or\
                (self.bs.no_more_static_jobs and self.flow_flags['void_taken'])) and\
                  self.job_scheduler.nb_pending_jobs:
                # The Agent observes the Environment
                observation = self.agent.observe(self.env)
                logging.info('Step %s', self.step)
                logging.info('Observation %s', observation)
                # The Agent decides which action to take
                action = self.agent.decide(observation)
                logging.info('Action %s', action)
                if action == self.env.action_size - 1 and self.env.with_void == True:
                    self.flow_flags['void_taken'] = True
                else:
                    self.flow_flags['void_taken'] = False
                # The Agent alters the Environment
                self.agent.alter(action, self.env)
                #Check initial time simulation
                if self.step == 0:
                    self.time_last_step = self.bs.time()
                self.step += 1
                self.flow_flags['action_taken'] = True
                self.flow_flags['jobs_submitted'] = self.flow_flags['jobs_completed'] = False
            # Modify resource states
            self.change_resource_states()
            # Treat case when a void action has been taken but there are still
            # pending jobs in spite of no more arrivals. This avoids deadlock.
            if self.bs.no_more_static_jobs and self.job_scheduler.pending_jobs\
               and self.flow_flags['void_taken']:
                self.onNoMoreEvents()
