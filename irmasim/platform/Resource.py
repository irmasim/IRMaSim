class Resource:

    def __init__(self, id: str, config: dict):
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

    def enumerate_ids(self,parent_id: list = []):
        if self.children:
            child_ids = []
            for child in self.children:
                child_ids += child.enumerate_ids(parent_id + [self.id])
            return child_ids
        else:
            return [ parent_id + [self.id] ]

    def enumerate_resources(self, resource_type):
        if issubclass(type(self), resource_type):
            return [self]
        else:
            if self.children:
                children = []
                for child in self.children:
                    children.extend(child.enumerate_resources(resource_type))
                return children
    
    def get_resource(self, resource_id: list):
            child = self.find_child(resource_id.pop(0))
            if resource_id == []:
                return child
            else:
                return child.get_resource(resource_id)

    def count_resources(self):
        if self.children:
            child_counts = []
            for child in self.children:
                child_counts += child.count_resources()
            counts = [sum(x) for x in zip(*child_counts)]
            return [1] + counts
        else:
            return [1]

    def full_id(self):
        if self.parent != None:
            id=self.parent.full_id()
            id.append(self.id)
            return id
        else:
            return [self.id]

    def __str__(self):
        return self.id + " ( " + ", ".join(map(str, self.children)) + " )"

    def pstr(self, indent: str, current: str = ""):
        return current + self.id + "\n" + "".join(map(lambda x: x.pstr(indent,current+indent), self.children))
