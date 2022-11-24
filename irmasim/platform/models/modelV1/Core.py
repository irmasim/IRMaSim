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
        self.clock_rate = config['clock_rate']
        self.mops = self.clock_rate * config['dpflops_per_cycle'] * 1e3
        self.speedup = 1.0
        self.task = None
        self.requested_memory_bandwidth = 0.0

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
            self.task.advance(delta_time, self.mops * 1e6 * self.speedup * delta_time)
            if self.task.ops <= 0.0:
                self.requested_memory_bandwidth = 0

    def reap(self, task: Task, resource_id: list):
        if self.task is None or self.task != task:
            raise Exception("Cannot reap task from resource")
        self.task = None
        self.requested_memory_bandwidth = 0

    def get_remaining_fraction(self):
        if self.task is None:
            return 0
        else:
            return self.task.ops/self.task.job.ops
