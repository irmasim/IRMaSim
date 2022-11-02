from irmasim.platform.models.modelV2.Cluster import Cluster
from irmasim.platform.models.modelV2.Node import Node
from irmasim.platform.TaskRunner import TaskRunner

class ModelBuilder:

    def __init__(self, platform_description: dict = None, library: dict = None, builder: "ModelBuilder" = None):
        if builder is not None:
            self.platform_description = builder.platform_description
            self.library = builder.library
        else:
            self.platform_description = platform_description
            self.library = library

    def build_platform(self):
        platform = TaskRunner(self.platform_description["id"], { "model": "modelV2" } )
        builder = ClusterBuilder(builder=self)
        self.build_children(builder, self.platform_description, platform, "clusters", "cluster")
        return platform

    def build_resource(self, id: str, definition: dict):
        pass

    def build_children(self, builder, definition: dict, resource, key, default_id):
        child_number = 0
        for child_definition in definition[key]:
            number = 1
            if "number" in child_definition.keys():
                number = child_definition["number"]
            for i in range(number):
                if "id" not in child_definition.keys():
                    child_id = default_id+str(child_number)
                else:
                    child_id = child_definition["id"]
                child = builder.build_resource(child_id, child_definition)
                resource.add_child(child)
                child_number += 1


class ClusterBuilder(ModelBuilder):

    def __init__(self, platform_description: dict = None, library: dict = None, builder: "ModelBuilder" = None):
        super(ClusterBuilder, self).__init__(platform_description=platform_description,
                                             library=library, builder=builder)

    def build_resource(self, id: str, definition: dict):
        resource = Cluster(id, {})
        builder = NodeBuilder(builder=self)
        self.build_children(builder, definition, resource, "nodes", "node")
        return resource


class NodeBuilder(ModelBuilder):

    def __init__(self, platform_description: dict = None, library: dict = None, builder: "ModelBuilder" = None):
        super(NodeBuilder, self).__init__(platform_description=platform_description,
                                          library=library, builder=builder)

    def build_resource(self, id: str, definition: dict):
        definition = self.library["node"][definition["type"]]
        resource = Node(id, definition)
        return resource
