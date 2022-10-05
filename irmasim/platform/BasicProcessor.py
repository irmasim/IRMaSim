from irmasim.platform.EnergyConsumer import EnergyConsumer
from irmasim.platform.TaskRunner import TaskRunner


class BasicProcessor(TaskRunner):

    def __init__(self, id: str, config: dict):
        super(BasicProcessor, self).__init__(id=id, config=config)
