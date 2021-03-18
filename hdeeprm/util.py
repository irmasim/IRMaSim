"""
Utilities for parsing and generating Workloads, Platforms and Resource Hierarchies.
"""

import json
import os.path as path
import pickle
from functools import partial

import defusedxml.minidom as mxml
import numpy
import numpy.random as nprnd
import resource as res
import logging

min_speed = 0.005
min_power = 0.005

def generate_workload(workload_file: str, shared_state: dict) -> (dict, dict):
    """ Parse workload file

Args:
    workload_file (str):
        Location of the Workload file in the system.
     shared_state (dict):
        Platform information.
    """

    # Load the reference speed for operations calculation
    reference_speed = numpy.mean(numpy.array([core.processor['gflops_per_core'] for core in shared_state['core_pool']]))
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

Args:
    platform_file_path (str):
        Identifier of the platform to generate.
    platform_file_path (str):
        Location of a file defining platforms.
    platform_library_path (str):
        Localtion of a library of components.
    """

    shared_state = {
        # Type of resources in the Platform
        'types': None,
        'gen_res_hierarchy': True,
        'counters': {'cluster': 0, 'node': 0, 'processor': 0, 'core': 0},
        # Core pool for filtering and selecting Cores is initially empty
        'core_pool': [],
        # Need to temporarly store information about up / down routes, since the XML DTD spec
        # imposes setting them at the end of generating all nodes. Initially, these are empty
        'udlink_routes': []
    }
    shared_state['types'] = _load_data(platform_file_path, platform_library_path)
    root_desc = shared_state['types']['platform'][platform_name]
    print(f'Using platform {platform_name}')
    root_el = None
    if shared_state['gen_res_hierarchy']:
        root_el = _root_el()
    _generate_clusters(shared_state, root_desc, root_el)

    return root_el, shared_state

def _load_data(platform_file_path: str, platform_library_path: str) -> dict:
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

def _root_el() -> dict:
    # Resource hierarchy starts on the Platform element
    return {
        'total_nodes': 0,
        'total_processors': 0,
        'total_cores': 0,
        'clusters': []
    }

def _generate_clusters(shared_state: dict, root_desc: dict, root_el: dict) -> None:
    for cluster_desc in root_desc['clusters']:
        cluster_el = None
        if shared_state['gen_res_hierarchy']:
            cluster_el = _cluster_el(root_el)
        _generate_nodes(shared_state, cluster_desc, cluster_el)
        shared_state['counters']['cluster'] += 1

def _cluster_el(root_el: dict) -> dict:
    cluster_el = {
        'platform': root_el,
        'local_nodes': []
    }
    root_el['clusters'].append(cluster_el)
    return cluster_el

def _generate_nodes(shared_state: dict, cluster_desc: dict, cluster_el: dict) -> None:
    for node_desc in cluster_desc['nodes']:
        for _ in range(node_desc['number']):
            node_el = None
            if shared_state['gen_res_hierarchy']:
                node_el = _node_el(shared_state, node_desc, cluster_el)
            _generate_processors(shared_state, node_desc, node_el)
            shared_state['counters']['node'] += 1

def _node_el(shared_state: dict, node_desc: dict, cluster_el: dict) -> dict:
    # Transform memory from GB to MB
    max_mem = shared_state['types']['node'][node_desc['type']]['memory']['capacity'] * 1000
    node_el = {
        'cluster': cluster_el,
        # Memory is tracked at Node-level
        'max_mem': max_mem,
        'current_mem': max_mem,
        'local_processors': []
    }
    cluster_el['platform']['total_nodes'] += 1
    cluster_el['local_nodes'].append(node_el)
    return node_el

def _generate_processors(shared_state: dict, node_desc: dict, node_el: dict) -> None:
    for proc_desc in shared_state['types']['node'][node_desc['type']]['processors']:
        # Computational capability per Core in FLOPs
        gflops_per_core = shared_state['types']['processor'][proc_desc['type']]['clock_rate'] *\
                         shared_state['types']['processor'][proc_desc['type']]['dpflops_per_cycle']
        # Power consumption per Core in Watts
        power_per_core = shared_state['types']['processor'][proc_desc['type']]['pa'] + \
                         (shared_state['types']['processor'][proc_desc['type']]['pb'] /\
                         shared_state['types']['processor'][proc_desc['type']]['cores'])
        proc_el = None
        gflops_per_core_xml = None
        power_per_core_xml = None
        gflops_per_core_xml, power_per_core_xml, p_state_with_speed = _proc_xml(gflops_per_core, power_per_core,
                                                shared_state['types']['processor'][proc_desc['type']]['pb'] /
                                                shared_state['types']['processor'][proc_desc['type']]['cores'])
        for _ in range(proc_desc['number']):
            if shared_state['gen_res_hierarchy']:
                proc_el = _proc_el(shared_state, proc_desc, node_el, gflops_per_core,
                                   power_per_core)
            _generate_cores(shared_state, gflops_per_core_xml, power_per_core_xml, proc_desc,
                            proc_el, p_state_with_speed)
            shared_state['counters']['processor'] += 1

def _proc_xml(gflops_per_core: float, dynamic_power_per_core: float, static_power_per_core: float) -> tuple:
    # For each processor several P-states are defined based on the number of p-state, with to more statics P-state
    # For each P-state it is compute the speed in fuction of the number of p-state

    gflops_list = ""
    p_state_with_speed = []

    for i in reversed(range(res.number_p_states)):
        gflops_list += f'{(gflops_per_core) * (1 / (res.number_p_states)) * (i + 1):.3f}Gf, '
        p_state_with_speed.append((gflops_per_core) * (1 / (res.number_p_states)) * (i + 1))


    gflops_list += f'{(gflops_per_core*min_speed):.3f}Gf, '
    gflops_list += f'{(gflops_per_core*min_speed):.3f}Gf'
    gflops_per_core_xml = {'speed': (gflops_list)}

    power_list = ""
    for i in reversed(range(res.number_p_states)):
        power_list+=(f'{(gflops_per_core) * (1 / (res.number_p_states)) * (i + 1):.3f}:{(dynamic_power_per_core):.3f},')

    power_list+=(f'{(gflops_per_core*min_speed):.3f}:{static_power_per_core:.3f},')
    power_list+=(f'{(gflops_per_core*min_speed):.3f}:{static_power_per_core*min_power:.3f}')

    power_per_core_xml = power_list
    return gflops_per_core_xml, power_per_core_xml, p_state_with_speed

def _proc_el(shared_state: dict, proc_desc: dict, node_el: dict, gflops_per_core: float,
             power_per_core: float) -> dict:
    #max_mem_bw = shared_state['types']['processor'][proc_desc['type']]['mem_bw']
    proc_el = {
        'node': node_el,
        'id': shared_state['counters']['processor'],
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
    return proc_el

def _generate_cores(shared_state: dict, gflops_per_core_xml: dict, power_per_core_xml: str,
                    proc_desc: dict, proc_el: dict, p_state_with_speed:list) -> None:
    for _ in range(shared_state['types']['processor'][proc_desc['type']]['cores']):
        if shared_state['gen_res_hierarchy']:
            _core_el(shared_state, proc_el, proc_desc, p_state_with_speed)
        shared_state['counters']['core'] += 1

def _core_el(shared_state: dict, proc_el: dict, proc_desc: dict, p_state_with_speed:list) -> None:
    proccesor = shared_state['types']['processor'][proc_desc['type']]
    core_el = res.Core(proc_el, shared_state['counters']['core'], shared_state['types']['processor']
                        [proc_desc['type']]['pa'], shared_state['types']['processor']
                        [proc_desc['type']]['pb']/shared_state['types']['processor']
                        [proc_desc['type']]['cores'], min_power, p_state_with_speed,
                        proccesor['c'], proccesor['da'], proccesor['dc'], proccesor['b'],
                       proccesor['dd'], proccesor['db'])

    proc_el['node']['cluster']['platform']['total_cores'] += 1
    proc_el['local_cores'].append(core_el)
    shared_state['core_pool'].append(core_el)
