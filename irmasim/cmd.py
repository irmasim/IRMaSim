import argparse as ap
import copy
import json
import sys
import os
import pickle
import os.path as path
import numpy as np
import random as rnd
import time
from irmasim.util import generate_workload, build_platform
from irmasim.Simulator import Simulator


def launch() -> None:

    start_time = time.time()
    parser = ap.ArgumentParser(description='Launches IRMaSim experiments')
    parser.add_argument('options_file', type=str, nargs='?', help='File defining the experiment in json format')
    parser.add_argument('-n', '--platform_name', type=str, help='Name of the platform to simulate')
    parser.add_argument('-p', '--platform_file', type=str, help='File with a description of elements of the platform')
    parser.add_argument('-w', '--workload_file', type=str, help='File with the workload definition')
    parser.add_argument('-o', '--output_dir', type=str, help='Directory for output files')

    parser.add_argument('-a', '--agent', type=str, help='File with the learning agent definition')
    parser.add_argument('-im', '--inmodel', type=str, help='Path for previous model loading')
    parser.add_argument('-om', '--outmodel', type=str, help='Path for saving new model, can be the same as the inmodel')
    parser.add_argument('-nr', '--nbruns', type=int, default=1, help='Number of simulations to run')
    parser.add_argument('-v', '--verbose', action="store_true", help='Remove prints in stdout')
    args = parser.parse_args()
    # Default options
    # TODO Use the random seed
    options = {'seed': 0, 'output_dir': '.'}
    # By default the library path is the data directory bundled with the code
    options['platform_library_path'] = path.join(path.dirname(__file__), 'data')

    if args.verbose:
        sys.stdout = open("/dev/null", "w")

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
    if args.agent:
        options['agent']['file'] = path.abspath(args.agent)
    if args.inmodel:
        options['agent']['input_model'] = path.abspath(args.inmodel)
    if args.outmodel:
        options['agent']['output_model'] = path.abspath(args.outmodel)

    # Check for minimum operating parameters
    if 'platform_name' not in options:
        parser.print_help()
        print('Need to specify a platform to simulate. Either with -n or in an options_file.')
        sys.exit(1)

    if 'workload_file' not in options:
        parser.print_help()
        print('Need to specify a workload to simulate. Either with -w or in an options_file.')
        sys.exit(1)

    # Set the seed for pseudo-random number generators
    print(f'Setting the random seed to {options["seed"]}')
    rnd.seed(options['seed'])
    np.random.seed(options['seed'])

    # Generate the Platform and Resource Hierarchy
    # TODO change model name to options data
    platform = build_platform(options['platform_name'], options.get('platform_file'),
                                            options['platform_library_path'] )

    # Generate the Workload
    job_limit, jobs = generate_workload(options['workload_file'], core_pool)

    data = {"job_limit": job_limit, "jobs": jobs, "platform": platform, "core_pool": core_pool}
    with open('{0}/data_tmp.pickle'.format(options['output_dir']), 'wb') as out_f:
        pickle.dump(data, out_f)

    for _ in range(args.nbruns):
        with open('{0}/data_tmp.pickle'.format(options['output_dir']), 'rb') as in_f:
            data = pickle.load(in_f)
        Simulator(data["job_limit"], data["jobs"], data["core_pool"],
                  data["platform"], copy.deepcopy(options))

    os.remove(options['output_dir'] + "/data_tmp.pickle")
    print("Execution time " + str(time.time() - start_time) + " seconds")
    sys.exit(0)
