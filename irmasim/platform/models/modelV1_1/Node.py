from irmasim.platform.BasicNode import BasicNode
from irmasim.Task import Task
import math


class Process:
    def __init__(self, node: 'Node', task: Task):
        self.node = node
        self.task = task
        self.requested_memory_bandwidth = task.memory_volume / \
                                          (task.ops / (self.node.gops * 1e9))
        self.speedup = 1

    def update_speedup(self):

        def ss(x):
            if x < 0:
                return 1
            elif x > 1:
                return 0
            else:
                return 1 - x * x * x * (x * (x * 6 - 15) + 10)

        def d(y, n):
            aux = (y - (self.node.da - n) * self.node.db) / (self.node.dc - n * self.node.dd)
            aux = ss(aux)
            return aux * (n * 0.6 / (1 + n * 0.6)) + 1 / (1 + n * 0.6)

        def perf(x, y, n):
            if x < self.node.c:
                return 1
            elif x > ((d(y, n) + self.node.b * self.node.c - 1) / self.node.b):
                return d(y, n)
            else:
                return self.node.b * (x - self.node.c) + 1

        other = len(self.node.processes) - 1
        all_bw = self.node.requested_memory_bandwidth
        int_bw = self.requested_memory_bandwidth

        self.speedup = round(perf(all_bw, int_bw, other), 9)

    def get_next_step(self):
        return self.task.ops / (self.node.gops * 1e9 * self.speedup)

    def advance(self, delta_time: float):
        self.task.advance(delta_time, self.node.gops * 1e9 * self.speedup * delta_time)

class Node (BasicNode):

    def __init__(self, id: list, config: dict):
        super(Node, self).__init__(id=id, config=config)
        self.processes = []
        self.gops = config['clock_rate']
        self.cores = config['cores']

        self.dynamic_power = config['dynamic_power']
        self.static_power = config['static_power']/config['cores']
        self.min_power = config['min_power']

        self.b = config['b']
        self.c = config['c']
        self.da = config['da']
        self.db = config['db']
        self.dc = config['dc']
        self.dd = config['dd']

        self.requested_memory_bandwidth = 0

    def get_mops(self):
        return self.gops*1e3

    def clock_rate(self):
        return self.gops

    def idle_cores(self):
        return self.cores - len(self.processes)

    def schedule(self, task: Task, resource_id: list):
        process = Process(self,task)
        self.processes.append(process)
        self.requested_memory_bandwidth += process.requested_memory_bandwidth
        self.update_speedup()

    def get_next_step(self):
        if self.processes == []:
            return math.inf
        else:
           return min([process.get_next_step() for process in self.processes])

    def advance(self, delta_time: float):
        for process in self.processes:
            process.advance(delta_time)

    def reap(self, task: Task, resource_id: list):
        for process in self.processes:
            if process.task == task:
                self.processes.remove(process)
                self.requested_memory_bandwidth -= process.requested_memory_bandwidth
                break
        self.update_speedup()

    def update_speedup(self):
        for process in self.processes:
            process.update_speedup()

    def get_joules(self, delta_time: float):
        task_count = len(self.processes)
        if task_count == 0:
            return self.min_power * delta_time
        else:
            return (self.dynamic_power * task_count + self.static_power * self.cores) * delta_time
