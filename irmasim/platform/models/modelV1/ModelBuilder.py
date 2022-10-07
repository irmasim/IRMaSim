from irmasim.platform.Resource import Resource
import pprint

from irmasim.platform.models.modelV1.Cluster import Cluster
from irmasim.platform.models.modelV1.Node import Node
from irmasim.platform.models.modelV1.Processor import Processor

from irmasim.platform.models.modelV1.Core import Core


class ModelBuilder:

    def __init__(self, platform_description: dict = None, library: dict = None, builder: "ModelBuilder" = None):
        if builder is not None:
            self.platform_description = builder.platform_description
            self.library = builder.library
        else:
            self.platform_description = platform_description
            self.library = library

    def build_platform(self):
        pprint.pprint(self.library)
        pprint.pprint(self.platform_description)
        platform = Resource(self.platform_description["id"], {})
        builder = ClusterBuilder(builder= self)
        self.build_children(builder, self.platform_description, platform, "clusters", "cluster")
        print(platform.pstr(""))
        return platform

    def build_resource(self, id: str, definition: dict):
        pass

    def build_children(self, builder, definition: dict, resource, key, default_id):
        for child_definition in definition[key]:
            number = 1
            if "number" in child_definition.keys():
                number = child_definition["number"]
            for i in range(number):
                if "id" not in child_definition.keys():
                    child_id = default_id
                else:
                    child_id = child_definition["id"]
                child = builder.build_resource(child_id + str(i), child_definition)
                resource.add_child(child)


class ClusterBuilder(ModelBuilder):

    def __init__(self, platform_description: dict = None, library: dict = None, builder: "ModelBuilder" = None):
        super(ClusterBuilder, self).__init__(platform_description=platform_description,
                                             library=library, builder=builder)

    def build_resource(self, id: str, definition: dict):
        resource = Cluster(id, {})
        builder = NodeBuilder(builder= self)
        self.build_children(builder, definition, resource, "nodes", "node")
        return resource


class NodeBuilder(ModelBuilder):

    def __init__(self, platform_description: dict = None, library: dict = None, builder: "ModelBuilder" = None):
        super(NodeBuilder, self).__init__(platform_description=platform_description,
                                          library=library, builder=builder)

    def build_resource(self, id: str, definition: dict):
        definition = self.library["node"][definition["type"]]
        resource = Node(id, definition)
        builder = ProcessorBuilder(builder= self)
        self.build_children(builder, definition, resource, "processors", "processor")
        return resource


class ProcessorBuilder(ModelBuilder):

    def __init__(self, platform_description: dict = None, library: dict = None, builder: "ModelBuilder" = None):
        super(ProcessorBuilder, self).__init__(platform_description=platform_description,
                                               library=library, builder=builder)

    def build_resource(self, id: str, definition: dict):
        definition = self.library["processor"][definition["type"]]
        resource = Processor(id, definition)
        builder = CoreBuilder(builder= self)
        for i in range(definition["cores"]):
            child = builder.build_resource("core" + str(i), definition)
            resource.add_child(child)

        return resource


class CoreBuilder(ModelBuilder):

    def __init__(self, platform_description: dict = None, library: dict = None, builder: "ModelBuilder" = None):
        super(CoreBuilder, self).__init__(platform_description=platform_description,
                                          library=library, builder=builder)

    def build_resource(self, id: str, definition: dict):
        return Core(id, definition)
