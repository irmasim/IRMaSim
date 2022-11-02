from irmasim.platform.BasicCore import BasicCore
from irmasim.Task import Task
import math


class Core(BasicCore):

    def __init__(self, id: list, config: dict):
        super(Core, self).__init__(id=id, config=config)
        self.dynamic_power = config['dynamic_power']
        self.static_power = config['static_power']/config['cores']
        self.min_power = config['min_power']
        self.b = config['b']
        self.c = config['c']
        self.da = config['da']
        self.db = config['db']
        self.dc = config['dc']
        self.dd = config['dd']
        self.mops = config['clock_rate'] * config['dpflops_per_cycle'] * 1e3
        self.speedup = 1.0
        self.task = None
        self.requested_memory_bandwidth = 0.0
        # TODO change to attributes
        self.state = {
            'current_power': self.min_power * self.static_power,
            'last_update': 0.0
        }

    def schedule(self, task: Task, resource_id: list):
        if self.task is not None:
            raise Exception("This core does not model oversubscription")

        self.task = task
        self.requested_memory_bandwidth = task.memory_volume / \
                                          (task.ops / (self.mops * 1e6))

    def get_next_step(self):
        if not self.task:
            return math.inf
        else:
            return self.task.ops / (self.mops * 1e6 * self.speedup)

    def advance(self, delta_time: float):
        if self.task is not None:
            self.task.ops -= self.mops * 1e6 * self.speedup * delta_time
            self.task.ops = math.floor(self.task.ops)
            if self.task.ops <= 0.0:
                self.requested_memory_bandwidth = 0

    def reap(self, task: Task, resource_id: list):
        if self.task is None or self.task != task:
            raise Exception("Cannot reap task from resource")
        self.task = None
        self.requested_memory_bandwidth = 0

    def delme(self):
        """
            else:
                self.update_completion(now)
            # 100% Power
            self.state['current_power'] = self.dynamic_power + self.static_power
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
            if state == "NEIGHBOURS-RUNNING":
                # Static Power
                self.state['current_power'] = self.static_power
            else:
                # Min Power
                self.state['current_power'] = self.min_power * self.static_power
        else:
            raise ValueError('Error: unknown State')
        self.state['speedup'] = speedup
        """
