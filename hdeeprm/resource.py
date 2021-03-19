"""
Core class and functionality for defining the Resource Hierarchy in the Decision System.
"""
import Job
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

    id (int): Unique identification. Also used in Batsim.
    state (dict): Defines the current state of the Core. Data fields:

      | pstate (:class:`int`) - P-state for the Core.
      | current_gflops (:class:`float`) - Current computing capability in GFLOPs.
      | current_power (:class:`float`) - Current power consumption in Watts.
      | served_job (batim.batsim.Job) - Job being served by the Core.
    """

    def __init__(self, processor: dict, id: int, dynamic_power:float, static_power:float, min_power:float,
                 c:int, da:int, dc:int, b:int, dd:int, db:int) -> None:
        self.processor = processor
        self.id = id
        self.dynamic_power = dynamic_power
        self.static_power = static_power
        self.min_power = min_power
        self.c = c
        self.da = da
        self.dc = dc
        self.b = b
        self.dd = dd
        self.db = db
        # By default, core is idle
        self.state = {
            'speedup': 0.0,
            'current_gflops': 0.0,
            'current_mem_bw': 0.0,
            'current_power': min_power * self.static_power,
            # When active, the Core is serving a Job which is stored as part of its state
            # Remaining operations and updates along simulation are tracked
            'served_job': None
        }

    def set_state(self, state: str, now: float, speedup : float = None, new_served_job: Job = None) -> None:
        """Sets the state of the Core.

It modifies the availability, computing speed and power consumption. It also establishes a new
served Job in case the Core is now active.

Args:
    new_pstate (int):
        New P-state for the Core.
    now (float):
        Current simulation time in seconds.
    new_served_job (batsim.batsim.Job):
        Reference to the Job now being served by the Core. Defaults to None.
        """

        # Active core
        if state == "RUN":
            if not self.state['served_job']:
                new_served_job.last_update = now
                self.state['served_job'] = new_served_job
                new_served_job.remaining_ops = new_served_job.req_ops
                self.state['current_mem_bw'] = new_served_job.mem_vol / \
                                               (new_served_job.req_ops / (self.processor['gflops_per_core'] * 1e9))

                self.processor['current_mem_bw'] += self.state['current_mem_bw']
                self.processor['node']['current_mem'] -= new_served_job.mem
            else:
                self.update_completion(now)
            # 100% Power
            self.state['current_power'] = self.dynamic_power + self.static_power
            self.state['current_gflops'] = self.processor['gflops_per_core'] * speedup * 1e9
        # Inactive core
        elif state in ("NEIGHBOURS-RUNNING", "IDLE"):
            if self.state['served_job']:
                self.processor['current_mem_bw'] -= self.state['current_mem_bw']
                self.processor['node']['current_mem'] += self.state['served_job'].mem
                self.state['current_mem_bw'] = 0
                self.state['served_job'] = None
            # 0% GFLOPS
            self.state['current_gflops'] = 0.0
            if state == "NEIGHBOURS-RUNNING":
                # Static Power
                self.state['current_power'] = self.static_power
            else:
                # Min Power
                self.state['current_power'] = self.min_power * self.static_power
        else:
            raise ValueError('Error: unknown State')
        self.state['speedup'] = speedup

    def update_completion(self, now: float) -> None:
        """Updates the Job operations left.

Calculates the amount of operations that have been processed using the time span from last update.

Args:
    now (float):
        Current simulation time in seconds.
        """

        time_delta = now - self.state['served_job'].last_update
        self.state['served_job'].remaining_ops -= self.state['current_gflops'] * time_delta
        self.state['served_job'].last_update = now

    def get_remaining_per(self) -> float:
        """Provides the remaining percentage of the Job being served.

Calculated by dividing the remaining operations by the total requested on arrival.
        """

        return self.state['served_job'].remaining_ops / self.state['served_job'].req_ops

    def __str__(self):
        return str(self.id) + ": " + str(self.processor['current_mem_bw']) + " " + str(
            self.processor['gflops_per_core'])

    def __lt__(self, other):
        return self.id < other.id