"""
Utilities for parsing and generating Workloads, Platforms and Resource Hierarchies.
"""

import json
import os.path as path
import heapq
import numpy
import irmasim.resource as res
from irmasim.Job import Job

# TODO: Make configurable
min_power = 0.05


def generate_workload(workload_file: str, core_pool: list) -> (dict, dict):

    # Load the reference speed for operations calculation
    reference_speed = numpy.mean(numpy.array([core.processor['gflops_per_core'] for core in core_pool]))
    # Load JSON workload file
    with open(workload_file, 'r') as in_f:
        workload = json.load(in_f)

    queue = []
    job_id = 0
    for job in workload['jobs']:
        queue.append(
            Job(job_id, job["id"], job['subtime'], job['res'], workload['profiles'][job['profile']], job['profile']))
        job_id = job_id + 1
    heapq.heapify(queue)

    # Calculate the job limits from the Workload
    job_limits = {
        'max_time': numpy.percentile(numpy.array(
            [workload['profiles'][job['profile']]['req_time'] for job in workload['jobs']]), 99),
        'max_core': numpy.percentile(numpy.array(
            [job['res'] for job in workload['jobs']]), 99),
        'max_mem': numpy.percentile(numpy.array(
            [workload['profiles'][job['profile']]['mem'] for job in workload['jobs']]), 99),
        'max_mem_vol': numpy.percentile(numpy.array(
            [workload['profiles'][job['profile']]['mem_vol'] for job in workload['jobs']]), 99)
    }
    return job_limits, queue

def _build_library(platform_file_path: str, platform_library_path: str) -> dict:
    types = {}
    for pair in [('platform', 'platforms.json'), ('network', 'network_types.json'), ('node', 'node_types.json'),
                 ('processor', 'processor_types.json')]:
        types[pair[0]] = {}
        lib_filename = path.join(platform_library_path, pair[1])
        if path.isfile(lib_filename):
            with open(lib_filename, 'r') as lib_f:
                print(f'Loading definitions from {lib_filename}')
                types.update({pair[0]: json.load(lib_f)})

    if platform_file_path:
        with open(platform_file_path, 'r') as in_f:
            print(f'Loading definitions from {platform_file_path}')
            types_from_file = json.load(in_f)
            for group in types_from_file:
                types[group].update(types_from_file[group])
    return types

def generate_platform(platform_name: str, platform_file_path: str, platform_library_path: str):

    library = _build_library(platform_file_path, platform_library_path)
    platform_description = library['platform'][platform_name]
    print(f'Using platform {platform_name}')
    import pprint
    pprint.pprint(library)
    Exception("AAAAAAAAAAAAAAAAAAA")
    return generate_cluster(platform_description)

def generate_cluster(platform_description: dict):
    pass
    """clusters = []
    for cluster in platform_description['clusters']:
        # TODO parseo del cluster json
        aux = Cluster(id, config))
        aux.children = generate_nodes(cluster, aux)
    return clusters
"""



