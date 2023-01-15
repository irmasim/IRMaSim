from irmasim.platform.BasicNode import BasicNode
from irmasim.platform.BasicProcessor import BasicProcessor
from irmasim.Task import Task


class Node (BasicNode):

    def __init__(self, id: list, config: dict):
        super(Node, self).__init__(id=id, config=config)
        self.current_memory = 0
        self.core_count = 0

    def add_child(self, child: BasicProcessor):
        super().add_child(child)
        self.core_count += len([ 1 for core in child.children ])

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

    @classmethod
    def header(klass):
        return "id,cores,busy_cores"

    def log_state(self):
        return ",".join(map(lambda x: str(x), [self.id, self.core_count, self.core_count-self.count_idle_cores()]))

