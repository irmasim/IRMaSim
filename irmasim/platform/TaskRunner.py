from irmasim.platform.Resource import Resource
from irmasim.platform.EnergyConsumer import EnergyConsumer
from irmasim.Task import Task
import math

class TaskRunner(Resource, EnergyConsumer):

    def __init__(self, id: str, config: dict):
        super(TaskRunner, self).__init__(id=id, config=config)

    def schedule(self, task: Task, resource_id: list):
        try:
            child = self.find_child(resource_id.pop(0))
            child.schedule(task, resource_id)
        except IndexError:
            raise Exception('Cannot schedule a task to an empty id')

    def get_next_step(self):
        return min([child.get_next_step() for child in self.children if child.get_next_step() > 0] or [math.inf])

    def advance(self, delta_time: float):
        for child in self.children:
            child.advance(delta_time)

    def reap(self, task: Task, resource_id: list):
        try:
            child = self.find_child(resource_id.pop(0))
            child.reap(task, resource_id)
        except IndexError:
            raise Exception('Cannot reap a task from an empty id')

    def get_joules(self, delta_time: float):
        return sum([child.get_joules(delta_time) for child in self.children])

    @classmethod
    def header(klass):
        return "Logging of this kind of resource has not been implemented"

    def log_state(self):
        return "Unimplemented"
