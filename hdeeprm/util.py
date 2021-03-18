"""
Utilities for parsing and generating Workloads, Platforms and Resource Hierarchies.
"""

import json
import os.path as path
from functools import partial
import pprint
import defusedxml.minidom as mxml
import numpy
import numpy.random as nprnd
import resource as res
import logging

min_speed = 0.005
min_power = 0.005

def generate_workload(workload_file: str, core_pool: dict) -> (dict, dict):
    """ Parse workload file

Args:
    workload_file (str):
        Location of the Workload file in the system.
     core_pool (dict):
        Platform information.
    """

    # Load the reference speed for operations calculation
    reference_speed = numpy.mean(numpy.array([core.processor['gflops_per_core'] for core in core_pool['pool']]))
    # Load JSON workload file
    with open(workload_file, 'r') as in_f:
        workload = json.load(in_f)
    num_instructions = workload.get("num_instructions")
    if num_instructions and num_instructions.lower() == "true":
        for profile in workload['profiles'].values():
            profile['cpu'] = profile['cpu'] / profile['ipc']
            profile['req_ops'] = profile['cpu']
            print("Req_ops y CPU %lf, %lf", profile['req_ops'], profile['cpu'])
    # Adjust operations for every profile
    else:
        for profile in workload['profiles'].values():
            profile['req_ops'] = reference_speed * profile['req_time'] * 1e9
            profile['cpu'] = profile['req_ops']
            print("Req_ops y CPU %lf, %lf",profile['req_ops'],profile['cpu'])
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
    logging.debug(job_limits)
    return job_limits, workload

def generate_platform(platform_name: str,platform_file_path: str, platform_library_path: str) -> (dict, list):
    """ Construct platform definition from platform name, file and library.

Based on the name of the platform and its definition, found either in the
platform file or the library, it constructs a hierarchy of dicts that
represents each element of the platform.

Args:
    platform_file_path (str):
        Identifier of the platform to generate.
    platform_file_path (str):
        Location of a file defining platforms.
    platform_library_path (str):
        Localtion of a library of components.
    """

    core_pool = {
        'counters': {'cluster': 0, 'node': 0, 'processor': 0, 'core': 0},
        # Core pool for filtering and selecting Cores is initially empty
        'pool': [],
    }
    library = _build_library(platform_file_path, platform_library_path)
    platform_description = library['platform'][platform_name]
    print(f'Using platform {platform_name}')
    platform = {
        'total_nodes': 0,
        'total_processors': 0,
        'total_cores': 0,
        'clusters': []
    }
    _generate_clusters(library, platform_description, core_pool, platform)
    print(f'Built platform with %s cluster, %s nodes, %s processors and %s cores' % (
          core_pool['counters']['cluster'], core_pool['counters']['node'],
          core_pool['counters']['processor'], core_pool['counters']['core']))
    return platform, core_pool

def _build_library(platform_file_path: str, platform_library_path: str) -> dict:
    types = {}
    for pair in [ ( 'platform', 'platforms.json' ), ( 'network', 'network_types.json' ), ( 'node', 'node_types.json' ), ( 'processor', 'processor_types.json' ) ]:
       types[pair[0]] = {}
       lib_filename = path.join(platform_library_path, pair[1])
       if path.isfile(lib_filename):
          with open(lib_filename, 'r') as lib_f:
             print(f'Loading definitions from {lib_filename}')
             types.update( { pair[0]: json.load(lib_f)} )

    if platform_file_path:
       with open(platform_file_path, 'r') as in_f:
           print(f'Loading definitions from {platform_file_path}')
           types_from_file = json.load(in_f)
           for group in types_from_file:
              types[group].update(types_from_file[group]);
    return types

def _generate_clusters(library: dict, root_desc: dict, core_pool: dict, root_el: dict) -> None:
    for cluster_desc in root_desc['clusters']:
        cluster_el = _cluster_el(root_el, core_pool)
        _generate_nodes(library, cluster_desc, core_pool, cluster_el)

def _cluster_el(root_el: dict, core_pool: dict) -> dict:
    cluster_el = {
        'platform': root_el,
        'local_nodes': []
    }
    root_el['clusters'].append(cluster_el)
    core_pool['counters']['cluster'] += 1
    return cluster_el

def _generate_nodes(library: dict, cluster_desc: dict, core_pool: dict, cluster_el: dict) -> None:
    for node_desc in cluster_desc['nodes']:
        for _ in range(node_desc['number']):
            node_el = _node_el(library, node_desc, core_pool, cluster_el)
            _generate_processors(library, node_desc, core_pool, node_el)

def _node_el(library: dict, node_desc: dict, core_pool: dict, cluster_el: dict) -> dict:
    # Transform memory from GB to MB
    max_mem = library['node'][node_desc['type']]['memory']['capacity'] * 1000
    node_el = {
        'cluster': cluster_el,
        # Memory is tracked at Node-level
        'max_mem': max_mem,
        'current_mem': max_mem,
        'local_processors': []
    }
    cluster_el['platform']['total_nodes'] += 1
    cluster_el['local_nodes'].append(node_el)
    core_pool['counters']['node'] += 1
    return node_el

def _generate_processors(library: dict, node_desc: dict, core_pool: dict, node_el: dict) -> None:
    for proc_desc in library['node'][node_desc['type']]['processors']:
        # Computational capability per Core in FLOPs
        gflops_per_core = library['processor'][proc_desc['type']]['clock_rate'] *\
                          library['processor'][proc_desc['type']]['dpflops_per_cycle']
        # Power consumption per Core in Watts
        power_per_core = library['processor'][proc_desc['type']]['pa'] + \
                         (library['processor'][proc_desc['type']]['pb'] /\
                         library['processor'][proc_desc['type']]['cores'])
        proc_el = None
        p_state_with_speed = _calculate_pstates(gflops_per_core, power_per_core,
                                       library['processor'][proc_desc['type']]['pb'] /
                                       library['processor'][proc_desc['type']]['cores'])
        for _ in range(proc_desc['number']):
            proc_el = _proc_el(library, proc_desc, gflops_per_core, power_per_core, core_pool, node_el)
            _generate_cores(library, proc_desc, p_state_with_speed, core_pool, proc_el)

def _calculate_pstates(gflops_per_core: float, dynamic_power_per_core: float, static_power_per_core: float) -> list:
    # For each processor several P-states are defined based on the number of p-state, with to more statics P-state
    # For each P-state it is compute the speed in fuction of the number of p-state

    p_state_with_speed = []
    for i in reversed(range(res.number_p_states)):
        p_state_with_speed.append((gflops_per_core) * (1 / (res.number_p_states)) * (i + 1))
    return p_state_with_speed

def _proc_el(library: dict, proc_desc: dict, gflops_per_core: float, power_per_core: float, core_pool: dict, node_el: dict) -> dict:
    #max_mem_bw = library['processor'][proc_desc['type']]['mem_bw']
    proc_el = {
        'node': node_el,
        'id': core_pool['counters']['processor'],
        # Memory bandwidth is tracked at Processor-level
        #TODO CAMBIARLO
        #'max_mem_bw': 0,
        'current_mem_bw': 0,
        'gflops_per_core': gflops_per_core,
        'power_per_core': power_per_core,
        'local_cores': []
    }
    node_el['cluster']['platform']['total_processors'] += 1
    node_el['local_processors'].append(proc_el)
    core_pool['counters']['processor'] += 1
    return proc_el

def _generate_cores(library: dict, proc_desc: dict, p_state_with_speed:list, core_pool: dict, proc_el: dict) -> None:
    for _ in range(library['processor'][proc_desc['type']]['cores']):
        _core_el(library, proc_desc, p_state_with_speed, core_pool, proc_el)

def _core_el(library: dict, proc_desc: dict, p_state_with_speed:list, core_pool: dict, proc_el: dict) -> None:
    processor = library['processor'][proc_desc['type']]
    core_el = res.Core(proc_el, core_pool['counters']['core'],
                        processor['pa'], processor['pb'] / processor['cores'],
                        min_power, p_state_with_speed, processor['c'],
                        processor['da'], processor['dc'], processor['b'], processor['dd'], processor['db'])

    proc_el['node']['cluster']['platform']['total_cores'] += 1
    proc_el['local_cores'].append(core_el)
    core_pool['pool'].append(core_el)
    core_pool['counters']['core'] += 1
