from irmasim.platform.BasicNode import BasicNode
from irmasim.platform.BasicProcessor import BasicProcessor
from irmasim.Task import Task


class Node (BasicNode):

    def __init__(self, id: list, config: dict):
        super(Node, self).__init__(id=id, config=config)
        self.current_memory = 0
        self.cores = 0

    def add_child(self, child: BasicProcessor):
        super().add_child(child)
        self.cores += len([ 1 for core in child.children ])

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
        return "id,cores,busy_cores"

    def log_state(self):
        return ",".join(map(lambda x: str(x), [self.id, self.cores, self.cores-self.count_idle_cores()]))

