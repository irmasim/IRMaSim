import importlib

import gym
import numpy as np

from irmasim.workload_manager.Environment import Environment

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from irmasim.workload_manager.Policy import Policy
from irmasim.Simulator import Simulator
from irmasim.Options import Options


class ActionEnvironment(Environment):

    def __init__(self, workload_manager: 'Policy', simulator: Simulator) -> None:
        self.workload_manager = workload_manager
        self.simulator = simulator
        self.env_options = Options().get()["workload_manager"]["environment"]

        self.NUM_JOBS = self.env_options["num_jobs"]
        self.NUM_NODES = self.env_options["num_nodes"]
        self.OBS_FEATURES = self.env_options["obs_features"]

        self.action_space = gym.spaces.Discrete(self.NUM_JOBS * self.NUM_NODES)

        options = Options().get()
        mod = importlib.import_module("irmasim.platform.models." + options["platform_model_name"] + ".Node")
        klass = getattr(mod, 'Node')
        self.resources = self.simulator.get_resources(klass)

        self.observation = self.observation_action
        self.observation_space = gym.spaces.Box(low=0.0, high=1.0,
                                                shape=(self.NUM_JOBS * self.NUM_NODES, self.OBS_FEATURES),
                                                dtype=np.float32)
        objective_to_reward = {
            'makespan': self.makespan_reward,
            'energy_consumption': self.energy_consumption_reward,
            'edp': self.edp_reward,
            'slowdown': self.slowdown_reward,
            'bounded_slowdown': self.bounded_slowdown_reward,
            'waiting_time': self.waiting_time_reward
        }
        if not self.env_options['objective'] in objective_to_reward:
            objectives = ", ".join(objective_to_reward.keys())
            raise Exception(f"Unknown objective {self.env_options['objective']}. Must be one of: {objectives}.")
        self.reward = objective_to_reward[self.env_options['objective']]

    @property
    def observation_size(self) -> tuple:
        return self.observation_space.shape

    def get_action_pair(self, action: int) -> tuple:
        job = action // self.NUM_NODES
        node = action % self.NUM_NODES
        return job, node
