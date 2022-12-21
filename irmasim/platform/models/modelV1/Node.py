from irmasim.platform.BasicNode import BasicNode
from irmasim.Task import Task


class Node (BasicNode):

    def __init__(self, id: list, config: dict):
        super(Node, self).__init__(id=id, config=config)
        self.current_memory = 0

    def count_idle_cores(self):
        count = 0
        for processor in self.children:
            count += len([ 1 for core in processor.children if core.task is None  ])
        return count

    def schedule(self, task: Task, resource_id: list):
        super().schedule(task, resource_id)
        self.current_memory += task.job.memory

    def reap(self, task: Task, resource_id: list):
        super().reap(task, resource_id)
        self.current_memory -= task.job.memory

    @classmethod
    def header(klass):
        return "id"

    def log_state(self):
        return self.id

