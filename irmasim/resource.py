"""
Core class and functionality for defining the Resource Hierarchy in the Decision System.
"""
import logging
from irmasim.Job import Job
import math

#TODO: Make configurable
min_power = 0.05

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

    def __init__(self, processor: dict, id: int) -> None:
        self.processor = processor
        self.id = id
        # By default, core is idle
        self.state = {
            'speedup': 0.0,
            'current_gflops': 0.0,
            'current_mem_bw': 0.0,
            'job_remaining_ops': 0.0,
            # When active, the Core is serving a Job which is stored as part of its state
            # Remaining operations and updates along simulation are tracked
            'served_job': None,
            'last_update' : 0.0
        }

    def set_state(self, state: str, now: float, speedup : float = 1, power : float = 0, new_served_job: Job = None) -> None:
        """Sets the state of the Core.

It modifies the availability, computing speed and power consumption. It also establishes a new
served Job in case the Core is now active.

Args:
    state:
        New state for the Core.
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
                self.state['job_remaining_ops'] = new_served_job.req_ops
                self.state['last_update'] = now
                self.state['current_mem_bw'] = new_served_job.mem_vol / \
                                               (new_served_job.req_ops / (self.processor['gflops_per_core'] * 1e9))

                self.processor['current_mem_bw'] += self.state['current_mem_bw']
                self.processor['node']['current_mem'] -= new_served_job.mem
            else:
                self.update_completion(now)
            self.state['current_power'] = power
            self.state['speedup'] = speedup
            self.state['current_gflops'] = self.processor['gflops_per_core'] * speedup * 1e9
        # Inactive core
        elif state in ("NEIGHBOURS-RUNNING", "IDLE"):
            if self.state['served_job']:
                self.processor['current_mem_bw'] -= self.state['current_mem_bw']
                self.processor['node']['current_mem'] += self.state['served_job'].mem
                self.state['current_mem_bw'] = 0
                self.state['served_job'] = None
            # 0% GFLOPS
            self.state['speedup'] = 0.0
            self.state['current_gflops'] = 0.0
        else:
            raise ValueError('Error: unknown State')
        self.state['speedup'] = speedup
        self.state['current_power'] = power

    def update_completion(self, now: float) -> None:
        """Updates the Job operations left.

Calculates the amount of operations that have been processed using the time span from last update.

Args:
    now (float):
        Current simulation time in seconds.
        """
        if self.state['served_job'] is not None:
            time_delta = round(now - self.state['last_update'], 9)
            self.state['job_remaining_ops'] -= math.ceil(self.state['current_gflops'] * time_delta)
            if self.state['job_remaining_ops'] <= 0:
                self.processor['current_mem_bw'] -= self.state['current_mem_bw']
                self.state['current_mem_bw'] = 0.0
                self.state['job_remaining_ops'] = 0
            self.state['last_update'] = now

    def get_remaining_per(self) -> float:
        """Provides the remaining percentage of the Job being served.

Calculated by dividing the remaining operations by the total requested on arrival.
        """

        return self.state['job_remaining_ops'] / self.state['served_job'].req_ops

    def __str__(self):
        return str(self.id) + ": " + str(self.processor['current_mem_bw']) + " " + str(
            self.processor['gflops_per_core'])

    def __lt__(self, other):
        return self.id < other.id

class Core_profile_1(Core):
    def __init__(self, proc_el: dict, id: int, config: dict) -> None:
        super().__init__(proc_el,id)
        self.dynamic_power = config['dynamic_power']
        self.static_power = config['static_power'] / config['cores']
        self.min_power = min_power
        self.b = config['b']
        self.c = config['c']
        self.da = config['da']
        self.db = config['db']
        self.dc = config['dc']
        self.dd = config['dd']
        self.state['current_power'] = self.power(state="IDLE", all_bw=0, job_count=0)

    def speedup(self, x: float, y: float, n: int):
        def ss(x):
            if x < 0:
                return 1
            elif x > 1:
                return 0
            else:
                return (1 - x*x*x*(x*(x*6-15)+10))

        def d(y, n):
            aux = (y-(self.da-n)*self.db)/(self.dc-n*self.dd)
            aux = ss(aux)
            return aux * (n*0.6/(1+n*0.6))+1/(1+n*0.6)

        if x < self.c:
            return 1
        elif x > ((d(y,n)+self.b*self.c-1)/self.b):
            return d(y,n)
        else:
            return self.b*(x-self.c)+1

    def max_power(self):
        return self.static_power+self.dynamic_power

    def power(self, state="RUN", all_bw=0.0, job_count=0, cores=1):
        if state == "RUN":
            # 100% Power
            return self.static_power+self.dynamic_power
        elif state == "NEIGHBOURS-RUNNING":
            # Static Power
            return self.static_power
        else:
            # Min Power
            return self.min_power * self.static_power

class Core_profile_2(Core):
    def __init__(self, proc_el: dict, id: int, config: dict) -> None:
        super().__init__(proc_el,id)
        self.aaa = config['aaa']
        self.aab = config['aab']
        self.aba = config['aba']
        self.abb = config['abb']
        self.baa = config['baa']
        self.bab = config['bab']
        self.bba = config['bba']
        self.bbb = config['bbb']
        self.caa = config['caa']
        self.cab = config['cab']
        self.cba = config['cba']
        self.cbb = config['cbb']
        self.cca = config['cca']
        self.ccb = config['ccb']
        self.daa = config['daa']
        self.dab = config['dab']
        self.dba = config['dba']
        self.dbb = config['dbb']
        self.pidle = config['pidle']
        self.p00 = config['p00']
        self.p01 = config['p01']
        self.p02 = config['p02']
        self.p10 = config['p10']
        self.p11 = config['p11']
        self.p20 = config['p20']
        self.state['current_power'] = self.power(state="IDLE", all_bw=0, job_count=0)
    
    def speedup(self, all_bw: float, int_bw: float, other: int):
        all_bw=all_bw*1e-3
        int_bw=int_bw*1e-3
        ab = self.abb + other * self.aba
        aa = self.aab + other * self.aaa

        bb = self.bbb + other * self.bba
        ba = self.bab + other * self.baa

        ca = self.cab + other * self.caa
        cb = self.cbb + other * self.cba
        cc = self.ccb + other * self.cca

        db = self.dbb + other * self.dba
        da = self.dab + other * self.daa

        a = ab + int_bw * aa
        b = bb + int_bw * ba
        c = cc + int_bw * cb + int_bw**2 * ca
        d = db + int_bw * da

        model = b+(c-b)*math.exp(-math.exp(a*(all_bw-d)))
        return model

    def max_power(self):
        return 100

    def power(self, state="RUN", all_bw=0.0, job_count=0, cores=1):
        if job_count == 0:
            return self.pidle/cores
        all_bw=all_bw*1e-6
        p = self.p00 + \
            self.p10 * all_bw + self.p20 * all_bw**2 + \
            self.p01 * job_count + self.p02 * job_count**2 + \
            self.p11 * all_bw * job_count 
        return p/cores
