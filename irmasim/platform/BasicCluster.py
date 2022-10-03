from irmasim.platform.EnergyConsumer import EnergyConsumer
from irmasim.platform.TaskRunner import TaskRunner


class BasicCluster(TaskRunner):

    def __init__(self):
        super(BasicCluster, self).__init__(id=id)
