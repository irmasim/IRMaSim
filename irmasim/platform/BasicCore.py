from irmasim.platform.EnergyConsumer import EnergyConsumer
from irmasim.platform.TaskRunner import TaskRunner


class BasicCore(TaskRunner ):

    def __init__(self, id: str):
        super(BasicCore, self).__init__(id=id)
        self.id = id


