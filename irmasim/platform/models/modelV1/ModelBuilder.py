from irmasim.platform.Resource import Resource
import pprint

from irmasim.platform.models.modelV1.Cluster import Cluster
from irmasim.platform.models.modelV1.Node import Node
from irmasim.platform.models.modelV1.Processor import Processor

from irmasim.platform.models.modelV1.Core import Core


class ModelBuilder:

    def __init__(self, platform_description: dict, library: dict):
        self.platform_description = platform_description
        self.library = library

    def build_platform(self):
        pprint.pprint(self.library)
        pprint.pprint(self.platform_description)
        platform = Resource(self.platform_description["id"], {})
        for cluster_definition in self.platform_description["clusters"]:
            number = 1
            if "number" in cluster_definition.keys():
                number = cluster_definition["number"]

            for i in range(number):
                cluster = self.build_resource(Cluster, cluster_definition["id"] + str(i), cluster_definition)
                platform.add_child(cluster)


    def build_resource(self, class_name, id: str, definition: dict):
        child_class = None
        key = None
        if class_name == Cluster:
            child_class = Node
            key = "nodes"
        elif class_name == Node:
            child_class = Processor
            key = "processors"
        elif class_name == Processor:
            child_class = Core
            key = "cores"

        if "type" in definition.keys() and key is not None:
            definition = self.library[str(class_name.__name__).lower()][definition["type"]]
            resource = class_name(id, definition)
        elif class_name == Core:
            resource = class_name(id, definition)
        else:
            resource = class_name(id, {})

        if key is not None:
            if key != "cores":
                pprint.pprint(definition)
                for child_definition in definition[key]:
                    number = 1
                    if "number" in child_definition.keys():
                        number = child_definition["number"]
            else:
                number = definition[key]
                child_definition = definition
            for i in range(number):
                child = self.build_resource(child_class, definition["id"] + str(i), child_definition)
                resource.add_child(child)
        print(resource)
        return resource
