#!/usr/bin/python3.6
# -*- coding: utf-8 -*-

import sys

sys.path.insert(0,'../hdeeprm')

from Simulator import Simulator
import heapq
from Job import Job
import resource as res
import json
import os.path as path

if __name__ == '__main__':
    job_limits = {
        'max_time': 10,
        'max_core': 1,
        'max_mem': 50,
        'max_mem_vol': 1000000
    }

    job1 = Job(0, 2, 1, {"req_ops": 1000000, "mem": 50, "ipc": 1,
                         "req_time":10, "mem_vol":1000000})


    cola = [job1]
    heapq.heapify(cola)

    platform = {
        'total_nodes': 1,
        'total_processors': 1,
        'total_cores': 1,
        'clusters': []
    }
    cluster = {
        'platform': platform,
        'local_nodes': []
    }
    platform["clusters"].append(cluster)

    nodo = {
        'cluster':cluster,
    # Memory is tracked at Node-level
    'max_mem': 50,
    'current_mem': 50,
    'local_processors': []
    }

    platform["clusters"][0]["local_nodes"].append(nodo)

    proc_el = {
        'node': nodo,
        'id': 0,
        'current_mem_bw': 0,
        'gflops_per_core': 0.001,
        'local_cores': []
    }
    platform["clusters"][0]["local_nodes"][0]['local_processors'].append(proc_el)
    core = res.Core(proc_el, 0, 100, 50, 0.05, -1.85e-05, 32000, 1.75, 3500, 45000, 3000)
    platform["clusters"][0]["local_nodes"][0]['local_processors'][0]['local_cores'].append(core)
    core_pool = [core]

    options = None

    with open('options.json', 'r') as in_f:
        options = json.load(in_f)
    options['seed'] = 0
    options['pybatsim']['output_dir'] = '.'
    options['pybatsim']['seed'] = 0
    options['pybatsim']['agent']['file'] = path.abspath('../agent_examples/actor_critic.py')
    options['agent'] = options['pybatsim']['agent']
    Simulator(job_limits, cola, core_pool, platform, options['pybatsim'])

