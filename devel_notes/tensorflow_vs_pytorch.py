import numpy as np

import tensorflow as tf
import torch
import torch.nn as nn
import torch.nn.functional as F

from torch.distributions.categorical import Categorical


tf.compat.v1.disable_eager_execution()

JOBS = 2
NODES = 2
FEATURES = 3



def combined_shape(length, shape=None):
    if shape is None:
        return (length,)
    return (length, shape) if np.isscalar(shape) else (length, *shape)

def placeholder(dim=None):
    return tf.compat.v1.placeholder(dtype=tf.float32, shape=combined_shape(None,dim))

def placeholders(*args):
    return [placeholder(dim) for dim in args]

def placeholder_obs(shape):
    return placeholder(shape)
def placeholder_action():
    return tf.compat.v1.placeholder(dtype=tf.int32, shape=(None,))



def run_tf(obs, mask):
    clip_ratio = 0.2
    pi_lr = 3e-4
    vf_lr = 1e-3
    def critic_mlp(x, act_dim):
        x = tf.reshape(x, shape=[-1, act_dim, FEATURES])
        x = tf.compat.v1.layers.dense(x, units=32, activation=tf.nn.relu, kernel_initializer=tf.compat.v1.keras.initializers.Constant(0.5), bias_initializer=tf.compat.v1.keras.initializers.Constant(0.5))
        x = tf.compat.v1.layers.dense(x, units=16, activation=tf.nn.relu, kernel_initializer=tf.compat.v1.keras.initializers.Constant(0.5), bias_initializer=tf.compat.v1.keras.initializers.Constant(0.5))
        x = tf.compat.v1.layers.dense(x, units=8, activation=tf.nn.relu, kernel_initializer=tf.compat.v1.keras.initializers.Constant(0.5), bias_initializer=tf.compat.v1.keras.initializers.Constant(0.5))
        x = tf.squeeze(tf.compat.v1.layers.dense(x, units=1, kernel_initializer=tf.compat.v1.keras.initializers.Constant(0.5), bias_initializer=tf.compat.v1.keras.initializers.Constant(0.5)), axis=-1)
        x = tf.compat.v1.layers.dense(x, units=64, activation=tf.nn.relu, kernel_initializer=tf.compat.v1.keras.initializers.Constant(0.5), bias_initializer=tf.compat.v1.keras.initializers.Constant(0.5))
        x = tf.compat.v1.layers.dense(x, units=32, activation=tf.nn.relu, kernel_initializer=tf.compat.v1.keras.initializers.Constant(0.5), bias_initializer=tf.compat.v1.keras.initializers.Constant(0.5))
        x = tf.compat.v1.layers.dense(x, units=8, activation=tf.nn.relu, kernel_initializer=tf.compat.v1.keras.initializers.Constant(0.5), bias_initializer=tf.compat.v1.keras.initializers.Constant(0.5))
        x = tf.compat.v1.layers.dense(x, units=1, kernel_initializer=tf.compat.v1.keras.initializers.Constant(0.5), bias_initializer=tf.compat.v1.keras.initializers.Constant(0.5))
        return x

    def rl_kernel(x, act_dim):
        x = tf.reshape(x, shape=[-1, act_dim, FEATURES])
        x = tf.compat.v1.layers.dense(x, units=32, activation=tf.nn.relu, kernel_initializer=tf.compat.v1.keras.initializers.Constant(0.5), bias_initializer=tf.compat.v1.keras.initializers.Constant(0.5))
        x = tf.compat.v1.layers.dense(x, units=16, activation=tf.nn.relu, kernel_initializer=tf.compat.v1.keras.initializers.Constant(0.5), bias_initializer=tf.compat.v1.keras.initializers.Constant(0.5))
        x = tf.compat.v1.layers.dense(x, units=8, activation=tf.nn.relu, kernel_initializer=tf.compat.v1.keras.initializers.Constant(0.5), bias_initializer=tf.compat.v1.keras.initializers.Constant(0.5))
        x = tf.squeeze(tf.compat.v1.layers.dense(x, units=1, kernel_initializer=tf.compat.v1.keras.initializers.Constant(0.5), bias_initializer=tf.compat.v1.keras.initializers.Constant(0.5)), axis=-1)
        return x
    def categorical_policy(x, a, mask):
        act_dim = JOBS * NODES
        output_layer = rl_kernel(x, act_dim)
        output_layer = output_layer + (mask - 1) * 1_000_000
        logp_all = tf.nn.log_softmax(output_layer)

        pi = tf.squeeze(tf.compat.v1.multinomial(output_layer, 1), axis=1)
        logp = tf.reduce_sum(tf.one_hot(a, depth=act_dim) * logp_all, axis=1)
        logp_pi = tf.reduce_sum(tf.one_hot(pi, depth=act_dim) * logp_all, axis=1)
        return pi, logp_all, logp, logp_pi, output_layer

    def actor_critic(x, a, mask):
        print('Comiiiing')
        with tf.compat.v1.variable_scope('pi'):
            pi, logp_all, logp, logp_pi, out = categorical_policy(x, a, mask)
        with tf.compat.v1.variable_scope('v'):
            v = tf.squeeze(critic_mlp(x, JOBS * NODES), axis=1)
        return pi, logp_all, logp, logp_pi, v, out

    print(obs)

    x_ph = placeholder_obs((JOBS * NODES * FEATURES,))
    a_ph = placeholder_action()
    mask_ph = placeholder(JOBS * NODES)
    adv_ph, ret_ph, logp_old_ph = placeholders(None, None, None)

    pi, logp_all, logp, logp_pi, v, out = actor_critic(x_ph, a_ph, mask_ph)

    all_phs = [x_ph, a_ph, mask_ph, adv_ph, ret_ph, logp_old_ph]
    get_action_ops = [pi, v, logp_all, logp_pi, out]

    # PPO objectives
    ratio = tf.exp(logp - logp_old_ph)  # pi(a|s) / pi_old(a|s)
    min_adv = tf.where(adv_ph > 0, (1 + clip_ratio) * adv_ph, (1 - clip_ratio) * adv_ph)
    pi_loss = -tf.reduce_mean(tf.minimum(ratio * adv_ph, min_adv))
    v_loss = tf.reduce_mean((ret_ph - v) ** 2)

    # Info (useful to watch during learning)
    approx_kl = tf.reduce_mean(logp_old_ph - logp)  # a sample estimate for KL-divergence, easy to compute
    approx_ent = tf.reduce_mean(-logp)  # a sample estimate for entropy, also easy to compute
    clipped = tf.logical_or(ratio > (1 + clip_ratio), ratio < (1 - clip_ratio))
    clipfrac = tf.reduce_mean(tf.cast(clipped, tf.float32))

    # Optimizers
    train_pi = tf.compat.v1.train.AdamOptimizer(learning_rate=pi_lr).minimize(pi_loss)
    train_v = tf.compat.v1.train.AdamOptimizer(learning_rate=vf_lr).minimize(v_loss)
    sess = tf.compat.v1.Session()
    sess.run(tf.compat.v1.global_variables_initializer())

    a, v_t, logp_all, logpi, output = sess.run(get_action_ops, feed_dict={x_ph: obs.reshape(1, -1), mask_ph: mask.reshape(1, -1)})
    print('a', a)
    print('v', v_t)
    print('logpall', logp_all)
    print('logpi', logpi)
    print('out', output)

    print('-' * 30)



class ActionActor(nn.Module):
    def __init__(self, actions_size: int, observation_size: int):
        super(ActionActor, self).__init__()
        self.input = nn.Linear(observation_size, 32)
        self.actor_hidden_0 = nn.Linear(32, 16)
        self.actor_hidden_1 = nn.Linear(16, 8)
        self.actor_output = nn.Linear(8, 1)

        self.input.weight.data.fill_(0.5)
        self.input.bias.data.fill_(0.5)
        self.actor_hidden_0.weight.data.fill_(0.5)
        self.actor_hidden_0.bias.data.fill_(0.5)
        self.actor_hidden_1.weight.data.fill_(0.5)
        self.actor_hidden_1.bias.data.fill_(0.5)
        self.actor_output.weight.data.fill_(0.5)
        self.actor_output.bias.data.fill_(0.5)

    def forward(self, observation: torch.Tensor, mask) -> tuple:
        #mask = torch.where(observation.sum(dim=-1) != 0.0, 1.0, 0.0).unsqueeze(dim=2)
        return self.forward_action(observation, mask)

    def forward_action(self, observation: torch.Tensor, mask: torch.Tensor) -> tuple:
        print('obs_size', observation.size(), mask.size())
        out_0 = F.leaky_relu(self.input(observation))
        out_1 = F.leaky_relu(self.actor_hidden_0(out_0))
        out_2 = F.leaky_relu(self.actor_hidden_1(out_1))
        out_3 = torch.squeeze(self.actor_output(out_2), dim=-1)
        out = out_3 + (mask - 1) * 1e6
        logp_all = F.log_softmax(out, dim=1)

        dist = Categorical(logits=out)
        pi = dist.sample()
        # BIEN HASTA AQUI

        #action = dist.sample()
        #print(action)
        print(dist)
        print(dist.log_prob(pi))

        #print('-'*10)
        #print(action.item())


        print('------')
        #print(torch.squeeze(F.softmax(out, dim=1), dim=2))


        # logp = torch.sum(F.one_hot(a) * logp_all, dim=1)
        logp_pi = torch.sum(F.one_hot(pi, 4) * logp_all, dim=1)
        return pi, logp_pi, logp_all, out  # Col of scores to row

    def loss(self, adv_ph, logp_old_ph) -> torch.Tensor:
        # TODO Definir el adv_buf y el actual size





        ratio = torch.exp(logp - logp_old_ph)
        min_adv = torch.where(adv_ph > 0, (1 + self.clip_ratio) * adv_ph, (1 - self.clip_ratio) * adv_ph)
        pi_loss = torch.mean(torch.minimum(ratio * adv_ph, min_adv))
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

        self.input.weight.data.fill_(0.5)
        self.input.bias.data.fill_(0.5)
        self.critic_hidden_0_0.weight.data.fill_(0.5)
        self.critic_hidden_0_0.bias.data.fill_(0.5)
        self.critic_hidden_0_1.weight.data.fill_(0.5)
        self.critic_hidden_0_1.bias.data.fill_(0.5)
        self.critic_hidden_0_2.weight.data.fill_(0.5)
        self.critic_hidden_0_2.bias.data.fill_(0.5)
        self.critic_hidden_1_0.weight.data.fill_(0.5)
        self.critic_hidden_1_0.bias.data.fill_(0.5)
        self.critic_hidden_1_1.weight.data.fill_(0.5)
        self.critic_hidden_1_1.bias.data.fill_(0.5)
        self.critic_hidden_1_2.weight.data.fill_(0.5)
        self.critic_hidden_1_2.bias.data.fill_(0.5)
        self.critic_output.weight.data.fill_(0.5)
        self.critic_output.bias.data.fill_(0.5)

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
        v_loss = torch.mean((torch.tensor(ret_ph) - torch.tensor(v)) ** 2)
        return v_loss




def run_torch(obs, mask):
    #print(obs)
    obs = torch.from_numpy(obs).float().unsqueeze(0)
    mask = torch.from_numpy(mask).float().unsqueeze(0)

    actor = ActionActor(JOBS * NODES, FEATURES)
    critic = ActionCritic(JOBS * NODES, FEATURES)
    pi, logpi, lopg_a, out = actor.forward(obs, mask)
    v = critic.forward(obs)
    print('a', pi)
    print('v', v)
    print('logpall', lopg_a)
    print('logpi', logpi)
    print('out', out)


if __name__ == '__main__':
    obs = np.array([0.2, 0.6, 0.2, 0.5, 0.1, 0.4, 0.3, 0.4, 0.3, 0.9, 0.01, 0.09], dtype=np.float32)
    mask = np.array([1.0, 1.0, 0.0, 1.0])

    run_tf(obs, mask)
    run_torch(obs.reshape((JOBS * NODES, FEATURES)), mask)
