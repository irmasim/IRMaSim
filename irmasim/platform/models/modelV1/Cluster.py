from irmasim.platform.BasicCluster import BasicCluster


class Cluster(BasicCluster):

    def __init__(self, id: list, config: dict):
        super(Cluster, self).__init__(id=id, config=config)
