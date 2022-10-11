from irmasim.platform.TaskRunner import TaskRunner


class BasicCore(TaskRunner):

    def __init__(self, id: str, config: dict):
        super(BasicCore, self).__init__(id=id, config=config)
