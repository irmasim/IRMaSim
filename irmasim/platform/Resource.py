class Resource:

    def __init__(self, id: str, config: dict):
        self.id = id
        self.children = []
        self.parent = None

    def find_child(self, id: str) -> object:
        for child in self.children:
            if child.id == id:
                return child
        Exception("Resource " + self.id + " does not have child " + id)

    def get_parent(self):
        return self.parent

    def build(self, library: dict, resource_name: str):
        pass