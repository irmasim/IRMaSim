class Resource:

    def __init__(self, id: list, config: dict):
        self.id = id
        self.config = config
        self.children = []
        self.parent = None

    def find_child(self, id: str):
        for child in self.children:
            if child.id == id:
                return child
        raise Exception("Resource " + self.id + " does not have child " + id)

    def get_parent(self):
        return self.parent

    def add_child(self, child: "Resource"):
        self.children.append(child)
        child.parent = self

    def __str__(self):
        return self.details() + " ( " + ", ".join(map(str, self.children)) + " )"

    def pstr(self, indent: str):
        return indent + self.details() + "\n" + "".join(map(lambda x: x.pstr(indent+" - "), self.children))

    def details(self):
        return ".".join(self.id)
