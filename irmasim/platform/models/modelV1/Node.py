from irmasim.platform.BasicNode import BasicNode


class Node (BasicNode):

    def __init__(self, id: list, config: dict):
        super(Node, self).__init__(id=id, config=config)
