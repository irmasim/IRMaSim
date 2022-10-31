from irmasim.platform.Resource import Resource
from irmasim.platform.EnergyConsumer import EnergyConsumer
from irmasim.Task import Task


class TaskRunner(Resource, EnergyConsumer):

    def __init__(self, id: str, config: dict):
        super(TaskRunner, self).__init__(id=id, config=config)

    def schedule(self, task: Task, resource_id: list):
        child = self.find_child(resource_id.pop(0))
        child.schedule(task, resource_id)

    def get_next_step(self):
        return min([child.get_next_step() for child in self.children])

    def advance(self, delta_time: float):
        for child in self.children:
            child.advance(delta_time)

    def reap(self, task: Task, resource_id: list):
        child = self.find_child(resource_id.pop(0))
        child.reap(task, resource_id)

    def get_joules(self, delta_time: float):
        return sum([child.get_joules(delta_time) for child in self.children])

