import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

from irmasim.workload_manager.agent.ActorCritic import ActorCritic


class ActionActorCritic(ActorCritic):

    def __init__(self, actions_size: int, observation_size: int) -> None:
        super().__init__(actions_size, observation_size)

        self.input = nn.Linear(observation_size, 32)
        self.actor_hidden_0 = nn.Linear(32, 16)
        self.actor_hidden_1 = nn.Linear(16, 8)
        self.actor_output = nn.Linear(8, 1)

        self.critic_hidden_0_0 = nn.Linear(32, 16)
        self.critic_hidden_0_1 = nn.Linear(16, 8)
        self.critic_hidden_0_2 = nn.Linear(8, 1)
        self.critic_hidden_1_0 = nn.Linear(actions_size, 64)
        self.critic_hidden_1_1 = nn.Linear(64, 32)
        self.critic_hidden_1_2 = nn.Linear(32, 8)
        self.critic_output = nn.Linear(8, 1)

    def decide(self, observation: np.ndarray) -> int:
        probs, value = self.forward(observation)
        print('Actor: ', probs)
        print('Critic: ', value)
        return self.get_action(probs)

    def forward(self, observation: np.ndarray) -> tuple:
        observation = torch.from_numpy(observation).float().unsqueeze(0)
        probs = self.forward_policy(observation)
        value = self.forward_value(observation)
        return probs, value

    def loss(self) -> float:
        return super().loss()

    def forward_policy(self, observation: torch.Tensor):
        out_0 = F.leaky_relu(self.input(observation))
        out_1 = F.leaky_relu(self.actor_hidden_0(out_0))
        out_2 = F.leaky_relu(self.actor_hidden_1(out_1))
        out = F.softmax(self.actor_output(out_2), dim=1)
        return torch.squeeze(out)

    def forward_value(self, observation: torch.Tensor):
        out_0_0 = F.leaky_relu(self.input(observation))
        out_0_1 = F.leaky_relu(self.critic_hidden_0_0(out_0_0))
        out_0_2 = F.leaky_relu(self.critic_hidden_0_1(out_0_1))
        out_0_3 = F.leaky_relu(self.critic_hidden_0_2(out_0_2))
        out_1 = torch.squeeze(out_0_3)
        out_1_1 = F.leaky_relu(self.critic_hidden_1_0(out_1))
        out_1_2 = F.leaky_relu(self.critic_hidden_1_1(out_1_1))
        out_1_3 = F.leaky_relu(self.critic_hidden_1_2(out_1_2))
        return self.critic_output(out_1_3)

    def calculate_advantages(self):
        pass





# TODO Remove
if __name__ == "__main__":
    JOBS = 3
    NODES = 4
    ac = ActionActorCritic(JOBS * NODES, 5)
    obs = np.random.uniform(0.0, 1.0, (JOBS*NODES, 5))
    print('INPUT: ', obs)
    print('--- End input')
    action = ac.decide(obs)
    print(action)
