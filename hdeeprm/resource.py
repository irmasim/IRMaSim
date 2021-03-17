"""
Core class and functionality for defining the Resource Hierarchy in the Decision System.
"""


import logging
number_p_states = 98 # Number of P-state less 2

class Core:
    """Core representing a compute resource in the Platform.

Cores process Jobs inside the Platform. They are uniquely identifiable in Batsim and provide a
computing capability for a given power consumption.

Attributes:
    processor (dict): Parent Processor data structure. Fields:

      | node (:class:`dict`) - Parent Node data structure. Fields:

        | cluster (:class:`dict`) - Parent Cluster data structure. Fields:

          | platform (:class:`dict`) - Root Platform data structure. Fields:

            | total_nodes (:class:`int`) - Total Nodes in the Platform.
            | total_processors (:class:`int`) - Total Processors in the Platform.
            | total_cores (:class:`int`) - Total Cores in the Platform.
            | job_limits (:class:`dict`) - Resource request limits for any Job. Fields:

              | max_time (:class:`int`) - Maximum requested time in seconds.
              | max_core (:class:`int`) - Maximum requested Cores.
              | max_mem (:class:`int`) - Maximum requested Memory in MB.
              | max_mem_bw (:class:`int`) - Maximum requested Memory BW in GB/s.
              | reference_machine (:class:`dict`) - Reference host for measures. Fields:

                | clock_rate (:class:`float`) - Machine clock speed.
                | dpflop_vector_width (:class:`int`) - Width of vector operations in 32B blocks.

            | reference_speed (:class:`float`) - Speed for tranforming time into operations.
            | clusters (list(:class:`dict`)) - Reference to all Clusters in the Platform.

          | local_nodes (list(:class:`dict`)) - Reference to local Nodes to the Cluster.

        | max_mem (:class:`int`) - Maximum memory capacity of the Node in MB.
        | current_mem (:class:`int`) - Current memory capacity of the Node in MB.
        | local_processors (list(:class:`dict`)) - Reference to local Procs to the Node.

      | max_mem_bw (:class:`float`) - Maximum memory BW capacity of the Processor in GB/s.
      | current_mem_bw (:class:`float`) - Current memory BW capacity of the Processor in GB/s.
      | gflops_per_core (:class:`float`) - Maximum GFLOPs per Core in the Processor.
      | power_per_core (:class:`float`) - Maximum Watts per Core in the Processor.
      | local_cores (list(:class:`.Core`)) - Reference to local Cores to the Processor.

    bs_id (int): Unique identification. Also used in Batsim.
    state (dict): Defines the current state of the Core. Data fields:

      | pstate (:class:`int`) - P-state for the Core.
      | current_gflops (:class:`float`) - Current computing capability in GFLOPs.
      | current_power (:class:`float`) - Current power consumption in Watts.
      | served_job (batim.batsim.Job) - Job being served by the Core.
    """

    def __init__(self, processor: dict, bs_id: int, dynamic_power:float, static_power:float, min_power:float,
                 p_state_with_speed:list, c:int, da:int, dc:int, b:int, dd:int, db:int) -> None:
        self.processor = processor
        self.bs_id = bs_id
        self.dynamic_power = dynamic_power
        self.static_power = static_power
        self.min_power = min_power
        self.p_state_with_speed = p_state_with_speed
        self.c = c
        self.da = da
        self.dc = dc
        self.b = b
        self.dd = dd
        self.db = db
        # By default, core is idle
        self.state = {
            'pstate': number_p_states + 1,
            'current_gflops': 0.0,
            'current_mem_bw': 0.0,
            'current_power': min_power * self.static_power,
            # When active, the Core is serving a Job which is stored as part of its state
            # Remaining operations and updates along simulation are tracked
            'served_job': None
        }