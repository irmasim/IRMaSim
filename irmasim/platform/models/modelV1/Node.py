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

    def idle_cores(self):
        cores = []
        for processor in self.children:
            cores.extend([ core for core in processor.children if core.task is None  ])
        return cores
    
    def count_cores(self):
        cores = 0
        for processor in self.children:
            cores += sum([ 1 for core in processor.children ])
        return cores

    def running_jobs(self):
        jobs = []
        for processor in self.children:
            jobs.extend([ core.task.job for core in processor.children if core.task is not None])
        return jobs

    def schedule(self, task: Task, resource_id: list):
        super().schedule(task, resource_id)
        self.current_memory += task.job.memory

    def reap(self, task: Task, resource_id: list):
        super().reap(task, resource_id)
        self.current_memory -= task.job.memory
