from irmasim.platform.TaskRunner import TaskRunner


class BasicNode(TaskRunner):

    def __init__(self, id: list, config: dict):
        super(BasicNode, self).__init__(id=id, config=config)
