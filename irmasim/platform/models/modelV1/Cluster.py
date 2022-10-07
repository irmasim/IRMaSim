from irmasim.platform.BasicCluster import BasicCluster


class Cluster(BasicCluster):

    def __init__(self, id: str, config: dict):
        super(Cluster, self).__init__(id=id, config=config)