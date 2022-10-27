from irmasim.platform.TaskRunner import TaskRunner


class BasicProcessor(TaskRunner):

    def __init__(self, id: list, config: dict):
        super(BasicProcessor, self).__init__(id=id, config=config)
