from irmasim.platform.TaskRunner import TaskRunner


class BasicCluster(TaskRunner):

    def __init__(self, id: str, config: dict):
        super(BasicCluster, self).__init__(id=id, config=config)
