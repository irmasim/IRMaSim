import argparse as ap
import matplotlib.pyplot as plt
import numpy as np


def plot_losses(exp_dir: str):
    with open(f'../{exp_dir}/losses.log', 'r') as l_f:
        losses_pairs = [tuple(map(float, lp.strip().split(','))) for lp in l_f.readlines()]

    plt.plot([l[0] for l in losses_pairs])
    plt.savefig(f'../{exp_dir}/pi_loss.png')
    plt.clf()

    plt.plot([l[1] for l in losses_pairs])
    plt.savefig(f'../{exp_dir}/v_loss.png')
    plt.clf()


def plot_rewards(exp_dir: str):
    with open(f'../{exp_dir}/rewards.log', 'r') as r_f:
        rews_pairs = [float(r.strip()) for r in r_f.readlines()]

    plt.plot([r for r in rews_pairs])
    plt.savefig(f'../{exp_dir}/rewards.png')
    plt.clf()


def do_plots(args):

    if args.loss:
        plot_losses(args.exp_dir)
    if args.reward:
        plot_rewards(args.exp_dir)


if __name__ == '__main__':
    parser = ap.ArgumentParser('Creates some plots with the results on the log files')
    parser.add_argument('-d', '--exp-dir', type=str, default='')
    parser.add_argument('-l', '--loss', default=False, action=ap.BooleanOptionalAction)
    parser.add_argument('-r', '--reward', default=False, action=ap.BooleanOptionalAction)
    args = parser.parse_args()
    do_plots(args)
