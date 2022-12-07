import numpy as np
from scipy.signal import lfilter
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.distributions import Categorical

from irmasim.workload_manager.agent.Agent import Agent


def discount_cumsum(x, discount):
    return lfilter([1], [1, float(-discount)], x[::-1], axis=0)[::-1]


class ActionActorCritic(Agent):

    def __init__(self, actions_size: int, observation_size: int) -> None:
        super(ActionActorCritic, self).__init__()
        self.actions_size = actions_size
        self.observation_size = observation_size
        self.actor = ActionActor(actions_size, observation_size)
        self.critic = ActionCritic(actions_size, observation_size)
        self.buffer = PPOBuffer(100)
        self.last_logp = 0
        self.last_v = 0
        self.last_rew = 0

    def decide(self, observation: np.ndarray) -> int:
        logp_all, probs, value = self.forward(observation)
        self.last_v = value
        return self.get_action(probs, logp_all)

    def get_action(self, probabilities: torch.Tensor, logp_all: torch.Tensor) -> int:
        dist = Categorical(logits=probabilities)
        action = dist.sample()
        logp_pi = torch.sum(F.one_hot(action, self.actions_size) * logp_all, dim=1)
        self.last_logp = dist.log_prob(action)
        return action.item()

    def forward(self, observation: np.ndarray) -> tuple:
        observation = torch.from_numpy(observation).float().unsqueeze(0)
        logp_all, out = self.actor.forward(observation)
        value = self.critic.forward(observation)
        return logp_all, out, value

    def loss(self):
        adv_ph, ret_ph, logp_old_ph, v_ph = map(lambda n: torch.tensor(n, requires_grad=True), self.buffer.get())
        policy_loss = self.actor.loss(adv_ph, logp_old_ph)
        value_loss = self.critic.loss(ret_ph, v_ph)
        return MultiLossWrapper(policy_loss, value_loss)
        #return policy_loss.sum() + value_loss.sum()

    def fixed_reward(self, rew: float):
        self.last_rew = rew
        self.store_values()

    def store_values(self):
        self.buffer.store(self.last_rew, self.last_v, self.last_logp)

    def finish_trajectory(self, rew: float):
        self.buffer.drop_last_values()
        self.last_rew = 0
        self.store_values()
        self.buffer.finish_path(rew)

    def state_dict(self):
        return {
            'actor': self.actor.state_dict(),
            'critic': self.critic.state_dict()
        }

    def load_state_dict(self, state_dict: dict):
        self.actor.load_state_dict(state_dict['actor'])
        self.critic.load_state_dict(state_dict['critic'])


class ActionActor(nn.Module):
    clip_ratio = 0.2

    def __init__(self, actions_size: int, observation_size: int):
        super(ActionActor, self).__init__()
        self.input = nn.Linear(observation_size, 32)
        self.actor_hidden_0 = nn.Linear(32, 16)
        self.actor_hidden_1 = nn.Linear(16, 8)
        self.actor_output = nn.Linear(8, 1)

    def forward(self, observation: torch.Tensor) -> tuple:
        mask = torch.where(observation.sum(dim=-1) != 0.0, 1.0, 0.0)
        return self.forward_action(observation, mask)

    def forward_action(self, observation: torch.Tensor, mask: torch.Tensor) -> tuple:
        out_0 = F.leaky_relu(self.input(observation))
        out_1 = F.leaky_relu(self.actor_hidden_0(out_0))
        out_2 = F.leaky_relu(self.actor_hidden_1(out_1))
        out_3 = torch.squeeze(self.actor_output(out_2), dim=-1)
        out = out_3 + (mask - 1) * 1e6
        logp_all = F.log_softmax(out, dim=1)
        return logp_all, out
        # logp = torch.sum(F.one_hot(a) * logp_all, dim=1)
        # logp_pi = torch.sum(F.one_hot(pi) * logp_all, dim=1)
        # return torch.squeeze(out)  # Col of scores to row

    def loss(self, adv_ph, logp_old_ph) -> torch.Tensor:
        # ratio = torch.exp(logp - logp_old_ph)
        min_adv = torch.where(adv_ph > 0, (1 + self.clip_ratio) * adv_ph, (1 - self.clip_ratio) * adv_ph)
        # pi_loss = torch.mean(torch.minimum(ratio * adv_ph, min_adv))
        pi_loss = torch.mean(min_adv)
        return pi_loss


class ActionCritic(nn.Module):
    def __init__(self, actions_size: int, observation_size: int):
        super(ActionCritic, self).__init__()
        self.input = nn.Linear(observation_size, 32)
        self.critic_hidden_0_0 = nn.Linear(32, 16)
        self.critic_hidden_0_1 = nn.Linear(16, 8)
        self.critic_hidden_0_2 = nn.Linear(8, 1)
        self.critic_hidden_1_0 = nn.Linear(actions_size, 64)
        self.critic_hidden_1_1 = nn.Linear(64, 32)
        self.critic_hidden_1_2 = nn.Linear(32, 8)
        self.critic_output = nn.Linear(8, 1)

    def forward(self, observation: torch.Tensor) -> torch.Tensor:
        out_0_0 = F.leaky_relu(self.input(observation))
        out_0_1 = F.leaky_relu(self.critic_hidden_0_0(out_0_0))
        out_0_2 = F.leaky_relu(self.critic_hidden_0_1(out_0_1))
        out_0_3 = F.leaky_relu(self.critic_hidden_0_2(out_0_2))
        out_1 = torch.squeeze(out_0_3)
        out_1_1 = F.leaky_relu(self.critic_hidden_1_0(out_1))
        out_1_2 = F.leaky_relu(self.critic_hidden_1_1(out_1_1))
        out_1_3 = F.leaky_relu(self.critic_hidden_1_2(out_1_2))
        return self.critic_output(out_1_3)

    def loss(self, ret_ph, v) -> torch.Tensor:
        v_loss = torch.mean((torch.Tensor(ret_ph) - torch.Tensor(v)) ** 2)
        return v_loss


class PPOBuffer:

    def __init__(self, size, gamma=0.99, lam=0.97):
        size = size * 100  # assume the traj can be really long
        self.adv_buf = np.zeros(size, dtype=np.float32)
        self.rew_buf = np.zeros(size, dtype=np.float32)
        self.ret_buf = np.zeros(size, dtype=np.float32)
        self.val_buf = np.zeros(size, dtype=np.float32)
        self.logp_buf = np.zeros(size, dtype=np.float32)
        self.gamma, self.lam = gamma, lam
        self.ptr, self.path_start_idx, self.max_size = 0, 0, size

    def store(self, rew, val, logp) -> None:
        """
        Append one timestep of agent-environment interaction to the buffer.
        """
        assert self.ptr < self.max_size  # buffer has to have room so you can store
        self.rew_buf[self.ptr] = rew
        self.val_buf[self.ptr] = val
        self.logp_buf[self.ptr] = logp
        self.ptr += 1

    def drop_last_values(self):
        self.ptr -= 1

    def finish_path(self, last_val) -> None:
        """
        Call this at the end of a trajectory, or when one gets cut off
        by an epoch ending. This looks back in the buffer to where the
        trajectory started, and uses rewards and value estimates from
        the whole trajectory to compute advantage estimates with GAE-Lambda,
        as well as compute the rewards-to-go for each state, to use as
        the targets for the value function.
        The "last_val" argument should be 0 if the trajectory ended
        because the agent reached a terminal state (died), and otherwise
        should be V(s_T), the value function estimated for the last state.
        This allows us to bootstrap the reward-to-go calculation to account
        for timesteps beyond the arbitrary episode horizon (or epoch cutoff).
        """

        path_slice = slice(self.path_start_idx, self.ptr)
        rews = np.append(self.rew_buf[path_slice], last_val)
        vals = np.append(self.val_buf[path_slice], last_val)

        # GAE-Lambda advantage calculation
        deltas = rews[:-1] + self.gamma * vals[1:] - vals[:-1]
        self.adv_buf[path_slice] = discount_cumsum(deltas, self.gamma * self.lam)

        # the next line computes rewards-to-go, to be targets for the value function
        self.ret_buf[path_slice] = discount_cumsum(rews, self.gamma)[:-1]

        self.path_start_idx = self.ptr

    def get(self) -> tuple:
        """
        Call this at the end of an epoch to get all the data from
        the buffer, with advantages appropriately normalized (shifted to have
        mean zero and std one). Also, resets some pointers in the buffer.
        """
        assert self.ptr < self.max_size
        actual_size = self.ptr
        self.ptr, self.path_start_idx = 0, 0

        actual_adv_buf = np.array(self.adv_buf, dtype=np.float32)
        actual_adv_buf = actual_adv_buf[:actual_size]
        adv_mean = np.mean(actual_adv_buf)
        adv_sum_sq = np.sum((actual_adv_buf - adv_mean) ** 2)
        adv_std = np.sqrt(adv_sum_sq / len(actual_adv_buf)) + 1e-5
        actual_adv_buf = (actual_adv_buf - adv_mean) / adv_std

        return actual_adv_buf, self.ret_buf[:actual_size], self.logp_buf[:actual_size], self.val_buf[:actual_size]


class MultiLossWrapper:
    def __init__(self, *losses):
        self.losses = [*losses]

    def backward(self):
        for loss in self.losses:
            loss.backward()

    def __repr__(self):
        return ','.join([str(l.item()) for l in self.losses])

# TODO Remove
if __name__ == "__main__":
    JOBS = 3
    NODES = 4
    ac = ActionActorCritic(JOBS * NODES + 4, 5)
    obs = np.random.uniform(0.0, 1.0, (JOBS * NODES, 5))
    obs = np.pad(obs, [(0, 4), (0, 0)])
    print('INPUT: ', obs)
    print('--- End input')
    action = ac.decide(obs)
    print(action)
    print('-----------------')
    t = torch.Tensor(obs)
    r = torch.Tensor(obs)
    s = torch.Tensor(obs)
    u = (t + r * s)

    mask = np.array(r.detach().numpy().sum(axis=1) != 0.0, dtype=np.float32)
    mask2 = torch.where(r.sum(dim=1) != 0.0, 1.0, 0.0)
    #out = ac.actor.forward_action(r, torch.Tensor(mask))


    print('-----------------')
    #print(out)
    print(mask)
    print(mask2)
    #print(out * torch.Tensor(mask))


