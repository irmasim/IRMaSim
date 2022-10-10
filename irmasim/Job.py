import math
from irmasim.Task import Task

class Job:

    def __init__(self, id: int, name: str, subtime: float, resources: int, profile: dict, type: str):
        self.id = id
        self.name = name
        self.type = type
        self.profile = profile
        self.subtime = subtime
        self.resources = resources
        self.ops = math.ceil(profile['req_ops'] / profile['ipc'])
        self.opc = profile['ipc']
        self.req_time = profile['req_time']
        self.memory = profile['mem']
        self.memory_vol = profile['mem_vol']
        self.generate_tasks()

    def is_job_finished(self):
        return sum([1 for task in self.tasks if task.ops > 0.0]) == 0

    def generate_tasks(self):
        self.tasks = []
        for task in range(self.resources):
            self.tasks.append(Task(self, self.ops, self.opc, self.memory,self.memory_vol))

    def __lt__(self, other):
        return self.subtime < other.subtime

    def __eq__(self, other):
        if other is None:
            return False
        return self.id == other.id
