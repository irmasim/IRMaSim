from irmasim.platform.BasicNode import BasicNode
from irmasim.Task import Task


class Node (BasicNode):

    def __init__(self, id: list, config: dict):
        super(Node, self).__init__(id=id, config=config)
        self.current_memory = 0

    def cores(self):
        return [ core for processor in self.children for core in processor.children ]

    def count_idle_cores(self):
        return len([ 1 for core in self.cores() if core.task is None ])

    def max_power_consumption(self):
        return sum([ processor.max_power_consumption for processor in self.children ])

    def schedule(self, task: Task, resource_id: list):
        super().schedule(task, resource_id)
        self.current_memory += task.job.memory

    def reap(self, task: Task, resource_id: list):
        super().reap(task, resource_id)
        self.current_memory -= task.job.memory
