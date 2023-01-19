import argparse as ap
import json
import sys
import os
import pickle
import os.path as path
import numpy as np
import random as rnd
import time
import logging
from irmasim.Simulator import Simulator
from irmasim.Options import Options
from irmasim.Job import Job

def launch() -> None:
    start_time = time.time()
    parser = ap.ArgumentParser(description='Launches IRMaSim experiments')
    parser.add_argument('options_file', type=str, nargs='?', help='File defining the experiment in json format')
    parser.add_argument('-n', '--platform_name', type=str, help='Name of the platform to simulate')
    parser.add_argument('-p', '--platform_file', type=str, help='File with a description of elements of the platform')
    parser.add_argument('-w', '--workload_file', type=str, help='File with the workload definition')
    parser.add_argument('-nt', '--nbtrajectories', type=str, help='Number of trajectories per run')
    parser.add_argument('-to', '--trajectory_origin', type=str, help='First job to submit')
    parser.add_argument('-tl', '--trajectory_length', type=str, help='Number of jobs to submit')
    parser.add_argument('-o', '--output_dir', type=str, help='Directory for output files')

    parser.add_argument('-wm', '--workload_manager', type=str, help='The type of workload manager to use')
    parser.add_argument('-a', '--agent', type=str, help='File with the learning agent definition')
    parser.add_argument('-im', '--inmodel', type=str, help='Path for previous model loading')
    parser.add_argument('-om', '--outmodel', type=str, help='Path for saving new model, can be the same as the inmodel')
    parser.add_argument('-nr', '--nbruns', type=int, default=1, help='Number of simulations to run')
    parser.add_argument('-ph', '--phase', type=str, default="train", help='Agent operation phase: train, eval')
    parser.add_argument('-v', '--verbose', action="store_true", help='Remove prints in stdout')
    parser.add_argument('-x', '--extra', type=str, action="append", help='Add arbitrary entries to configuration')
    args = parser.parse_args()

    if args.verbose:
        sys.stdout = open("/dev/null", "w")

    options = Options().get()

    # Load options from config file
    if args.options_file:
        print(f'Loading options from {args.options_file}')
        with open(args.options_file, 'r') as in_f:
            options.update(json.load(in_f))

    # Override config file options with command line arguments
    if args.platform_name:
        options['platform_name'] = args.platform_name
    if args.platform_file:
        options['platform_file'] = args.platform_file
    if args.workload_file:
        options['workload_file'] = args.workload_file
    if not 'nbtrajectories' in options:
        options['nbtrajectories'] = '1'
    if args.nbtrajectories:
        options['nbtrajectories'] = args.nbtrajectories
    if not 'trajectory_origin' in options:
        options['trajectory_origin'] = '0'
    if args.trajectory_origin:
        options['trajectory_origin'] = args.trajectory_origin
    if not 'trajectory_length' in options:
        options['trajectory_length'] = '0'
    if args.trajectory_length:
        options['trajectory_length'] = args.trajectory_length
    if args.output_dir:
        options['output_dir'] = args.output_dir
    else:
        if not 'output_dir' in options:
            options['output_dir'] = "."

    if not 'workload_manager' in options:
        options['workload_manager'] = {}
    if not type(options['workload_manager']) is dict:
        print('The workload_manager item in the options_file must be a dictionary.')
        sys.exit(1)


    if args.workload_manager:
        options['workload_manager']['type'] = args.workload_manager
    else:
        if not 'type' in options['workload_manager']:
            options['workload_manager']['type'] = "Minimal"
    
    if not 'agent' in options['workload_manager']:
        options['workload_manager']['agent'] = {}
    if args.agent:
        options['workload_manager']['agent']['name'] = path.abspath(args.agent)
    if args.inmodel:
        options['workload_manager']['agent']['input_model'] = path.abspath(args.inmodel)
    if args.outmodel:
        options['workload_manager']['agent']['output_model'] = path.abspath(args.outmodel)
    if args.phase:
        options['workload_manager']['agent']['phase'] = args.phase

    # TODO: This is very quick and dirty. Improve!
    if args.extra:
        for extra in args.extra:
            dictionary = options
            for part in extra.split("."):
                pair = part.split("=")
                if len(pair) == 1:
                    dictionary=dictionary[pair[0]]
                else:
                    dictionary[pair[0]]=pair[1]

    # Check for minimum operating parameters
    if 'platform_name' not in options:
        parser.print_help()
        print('Need to specify a platform to simulate. Either with -n or in an options_file.')
        sys.exit(1)

    if 'workload_file' not in options:
        parser.print_help()
        print('Need to specify a workload to simulate. Either with -w or in an options_file.')
        sys.exit(1)

    if 'workload_manager' not in options:
        parser.print_help()
        print('Need to specify a workload manager to simulate. Either with -w or in an options_file.')
        sys.exit(1)

    # Set the seed for pseudo-random number generators
    print(f"Setting the random seed to {options['seed']}")
    rnd.seed(options['seed'])
    np.random.seed(options['seed'])

    start_logging()
    simulator_handler = logging.getLogger("simulator").handlers[0]
    job_handler = logging.getLogger("jobs").handlers[0]
    resource_handler = logging.getLogger("resources").handlers[0]
    for run in range(args.nbruns):
        simulator = Simulator()
        print(f'Starting simulation run: {run}')
        simulator_handler.setFormatter(logging.Formatter(f'{run},%(message)s'))
        job_handler.setFormatter(logging.Formatter(f'{run},%(message)s'))
        resource_handler.setFormatter(logging.Formatter(f'{run},%(message)s'))
        simulator.start_simulation()
        print_statistics("Simulation time:", simulator.simulation_time_statistics())
        print_statistics("Energy consumption:", simulator.energy_consumption_statistics())
        print_statistics("Jobs:", simulator.job_statistics())
        print_statistics("Slowdown: ",simulator.slowdown_statistics())
        print_statistics("Bounded Slowdown: ",simulator.bounded_slowdown_statistics())
        print_statistics("Waiting Time: ",simulator.waiting_time_statistics())

    #os.remove(options['output_dir'] + "/simulator.pickle")
    print("Execution time " + str(time.time() - start_time) + " seconds")

    sys.exit(0)

def print_statistics(message: str, stats: dict):

    total_message = message
    for s in stats.items():
        total_message += " "+ str(s[0])+": " + str(s[1])+","
    
    print(total_message[:-1])
    #print(f"{message} total: {stats['total']}, avg: {stats['avg']}, max: {stats['max']}, min: {stats['min']}")

def start_logging():
    options = Options().get()
    levels = { 'DEBUG': logging.DEBUG, 'INFO': logging.INFO }
    irmasim_logger = logging.getLogger("irmasim")
    FileOutputHandler = logging.FileHandler(options['output_dir']+"/"+"irmasim.log", mode="w")
    if 'log_level' in options:
        irmasim_logger.setLevel(levels[options['log_level']])
    else:
        irmasim_logger.setLevel(logging.INFO)
    irmasim_logger.addHandler(FileOutputHandler)

    simulator_logger = logging.getLogger("simulator")
    FileOutputHandler = logging.FileHandler(options['output_dir']+"/"+"simulation.log", mode="w")
    FileOutputHandler.setFormatter(logging.Formatter(f'run,%(message)s'))
    simulator_logger.setLevel(logging.INFO)
    simulator_logger.addHandler(FileOutputHandler)
    simulator_logger.info(Simulator.header())
    simulator_logger.propagate = False

    job_logger = logging.getLogger("jobs")
    FileOutputHandler = logging.FileHandler(options['output_dir']+"/"+"jobs.log", mode="w")
    FileOutputHandler.setFormatter(logging.Formatter(f'run,%(message)s'))
    job_logger.setLevel(logging.INFO)
    job_logger.addHandler(FileOutputHandler)
    job_logger.info(Job.header())
    job_logger.propagate = False

    resource_logger = logging.getLogger("resources")
    FileOutputHandler = logging.FileHandler(options['output_dir']+"/"+"resources.log", mode="w")
    FileOutputHandler.setFormatter(logging.Formatter(f'run,%(message)s'))
    resource_logger.setLevel(logging.INFO)
    resource_logger.addHandler(FileOutputHandler)
    resource_logger.propagate = False
