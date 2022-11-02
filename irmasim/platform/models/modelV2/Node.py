from irmasim.platform.BasicNode import BasicNode
from irmasim.Task import Task
import math


class Process:
    def __init__(self, node: 'Node', task: Task):
        self.node = node
        self.task = task
        self.speedup = 1

    def get_next_step(self):
            return self.task.ops / (self.node.gops * 1e9 * self.speedup)

    def advance(self, delta_time: float):
        self.task.ops -= math.ceil(self.node.gops * 1e9 * self.speedup * delta_time)

class Node (BasicNode):

    def __init__(self, id: list, config: dict):
        super(Node, self).__init__(id=id, config=config)
        self.processes = []
        self.gops = config['clock_rate']

    def schedule(self, task: Task, resource_id: list):
        self.processes.append(Process(self,task))

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
                break
