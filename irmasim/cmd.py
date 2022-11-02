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
from irmasim.Job import job_header

def launch() -> None:
    start_time = time.time()
    parser = ap.ArgumentParser(description='Launches IRMaSim experiments')
    parser.add_argument('options_file', type=str, nargs='?', help='File defining the experiment in json format')
    parser.add_argument('-n', '--platform_name', type=str, help='Name of the platform to simulate')
    parser.add_argument('-p', '--platform_file', type=str, help='File with a description of elements of the platform')
    parser.add_argument('-w', '--workload_file', type=str, help='File with the workload definition')
    parser.add_argument('-o', '--output_dir', type=str, help='Directory for output files')

    parser.add_argument('-wm', '--workload_manager', type=str, help='The type of workload manager to use')
    parser.add_argument('-a', '--agent', type=str, help='File with the learning agent definition')
    parser.add_argument('-im', '--inmodel', type=str, help='Path for previous model loading')
    parser.add_argument('-om', '--outmodel', type=str, help='Path for saving new model, can be the same as the inmodel')
    parser.add_argument('-nr', '--nbruns', type=int, default=1, help='Number of simulations to run')
    parser.add_argument('-ph', '--phase', type=str, default="train", help='Agent operation phase: train, eval')
    parser.add_argument('-v', '--verbose', action="store_true", help='Remove prints in stdout')
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
    if args.output_dir:
        options['output_dir'] = args.output_dir
        if not path.exists(options['output_dir']):
            os.mkdir(options['output_dir'])
    else:
        options['output_dir'] = "."

    if not 'workload_manager' in options:
        options['workload_manager'] = {}

    if args.workload_manager:
        options['workload_manager']['type'] = path.abspath(args.workload_manager)
    else:
        if not 'type' in options['workload_manager']:
            options['workload_manager']['type'] = "Minimal"
    if args.agent:
        options['workload_manager']['agent'] = {}
        options['workload_manager']['agent']['file'] = path.abspath(args.agent)
        if args.inmodel:
            options['workload_manager']['agent']['input_model'] = path.abspath(args.inmodel)
        if args.outmodel:
            options['workload_manager']['agent']['output_model'] = path.abspath(args.outmodel)
        if args.phase:
            options['workload_manager']['agent']['phase'] = args.phase

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

    #with open('{0}/simulator.pickle'.format(options['output_dir']), 'wb') as out_f:
    #    pickle.dump(simulator, out_f)

    for _ in range(args.nbruns):
        #with open('{0}/simulator.pickle'.format(options['output_dir']), 'rb') as in_f:
        #    simulator = pickle.load(in_f)
        simulator = Simulator()
        simulator.start_simulation()

    #os.remove(options['output_dir'] + "/simulator.pickle")
    print("Execution time " + str(time.time() - start_time) + " seconds")
    sys.exit(0)


def start_logging():
    irmasim_logger = logging.getLogger("irmasim")
    FileOutputHandler = logging.FileHandler("irmasim.log", mode="w")
    irmasim_logger.setLevel(logging.DEBUG)
    irmasim_logger.addHandler(FileOutputHandler)

    simulator_logger = logging.getLogger("simulator")
    FileOutputHandler = logging.FileHandler("simulation.log", mode="w")
    simulator_logger.setLevel(logging.INFO)
    simulator_logger.addHandler(FileOutputHandler)

    job_logger = logging.getLogger("jobs")
    FileOutputHandler = logging.FileHandler("jobs.log", mode="w")
    job_logger.setLevel(logging.INFO)
    job_logger.addHandler(FileOutputHandler)
    job_logger.info(job_header())


