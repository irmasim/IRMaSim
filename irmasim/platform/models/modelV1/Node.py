from irmasim.platform.BasicNode import BasicNode
from irmasim.Job import Job


class Node (BasicNode):

    def __init__(self, id: str, config: dict):
        super(Node, self).__init__(id=id, config=config)
