from irmasim.platform.Resource import Resource
from irmasim.platform.EnergyConsumer import EnergyConsumer


class TaskRunner(Resource, EnergyConsumer):

    def __init__(self, id: str, config: dict):
        super(TaskRunner, self).__init__(id=id, config=config)

    """
    {
        cluster1 : [
            node1 : [],
            node2 : []
        ],
        cluster2 : [],
        cluster3 : []
    }
    
    """

    def schedule(self, tasks: list):
        for task in tasks:
            child = self.find_child(task.resource.pop(0))
            self.pre_schedule([task])
            child.schedule([task])

    def pre_schedule(self):
        pass

    def get_next_step(self):
        return min([child.get_next_step() for child in self.children])

    def advance(self, delta_time: float):
        for child in self.children:
            child.advance(delta_time)

    def reap(self, tasks: list):
        for task in tasks:
            child = self.find_child(task.resource.pop(0))
            child.reap([task])

    def get_joules(self, delta_time: float):
        return sum([child.get_joules() for child in self.children])

    def enumerate_resources(self):
        if self.children:
            return [self.id + child.enumerate_resources() for child in self.children]
        else:
            return [self.id]
