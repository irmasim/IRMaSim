from irmasim.platform.BasicProcessor import BasicProcessor
from irmasim.platform.BasicCore import BasicCore
from irmasim.Task import Task


class Processor (BasicProcessor):

    def __init__(self, id: list, config: dict):
        super(Processor, self).__init__(id=id, config=config)
        self.mops_per_core = config['clock_rate'] * config['dpflops_per_cycle'] * 1e3
        self.requested_memory_bandwidth = 0.0
        self.power_consumption = 0.0
        self.max_power_consumption = 0.0
        self.update_power()

    def add_child(self, child: BasicCore):
        super().add_child(child)
        self.max_power_consumption += child.dynamic_power + child.static_power

    def schedule(self, task: Task, resource_id: list):
        super().schedule(task, resource_id)
        self.update_speedup()
        self.update_power()

    def advance(self, delta_time: float):
        super().advance(delta_time)

    def reap(self, task: Task, resource_id: list):
        super().reap(task, resource_id)
        self.update_speedup()
        self.update_power()

    def get_joules(self, delta_time: float):
        return self.power_consumption * delta_time

    def update_speedup(self):

        def ss(x):
            if x < 0:
                return 1
            elif x > 1:
                return 0
            else:
                return 1 - x * x * x * (x * (x * 6 - 15) + 10)

        def d(y, n):
            aux = (y - (core.da - n) * core.db) / (core.dc - n * core.dd)
            aux = ss(aux)
            return aux * (n * 0.6 / (1 + n * 0.6)) + 1 / (1 + n * 0.6)

        def perf(x, y, n):
            if x < core.c:
                return 1
            elif x > ((d(y, n) + core.b * core.c - 1) / core.b):
                return d(y, n)
            else:
                return core.b * (x - core.c) + 1

        self.requested_memory_bandwidth = sum([core.requested_memory_bandwidth for core in self.children])
        task_count = sum([1 for core in self.children if core.task is not None and core.task.ops > 0.0])
        for core in self.children:
            if core.task is not None:
                core.speedup = round(perf(self.requested_memory_bandwidth, core.requested_memory_bandwidth,
                                  task_count - 1), 9)
            else:
                # Avoid speedup 0.9999
                core.speedup = 1

    def update_power(self):
        task_count = sum([1 for core in self.children if core.task is not None])
        if task_count == 0:
            self.power_consumption = sum([(core.min_power*core.static_power) for core in self.children])
        else:
            self.power_consumption = (sum([core.dynamic_power for core in self.children if core.task is not None]) +
                                      sum([core.static_power for core in self.children]))
