import math
from irmasim.Task import Task


class Job:

    def __init__(self, id: int, name: str, submit_time: float, resources: int, profile: dict, type: str):
        self.tasks = None
        self.id = id
        self.name = name
        self.type = type
        self.profile = profile
        self.submit_time = submit_time
        self.start_time = math.inf
        self.finish_time = 0.0
        self.resources = resources
        self.ops = math.ceil(profile['req_ops'] / profile['ipc'])
        self.opc = profile['ipc']
        self.req_time = profile['req_time']
        self.memory = profile['mem']
        self.memory_vol = profile['mem_vol']
        self.generate_tasks()

    def is_job_finished(self):
        for task in self.tasks:
            print(task)
        return sum([1 for task in self.tasks if task.ops > 0.0]) == 0

    def generate_tasks(self):
        self.tasks = []
        for task in range(self.resources):
            self.tasks.append(Task(self, self.ops, self.opc, self.memory, self.memory_vol))

    def set_start_time(self, time: float):
        if self.start_time > time:
            self.start_time = time

    def __lt__(self, other):
        return self.submit_time < other.submit_time

    def __eq__(self, other):
        if other is None:
            return False
        return self.id == other.id

    def __str__(self):
        resources = ";".join([".".join(task.resource) for task in self.tasks])
        return ",".join(map(lambda x: str(x), [self.id, self.submit_time, self.start_time, self.finish_time,
                                                self.finish_time - self.start_time, self.ops, self.type, resources]))

def job_header():
    return "id,submit_time,start_time,finish_time,execution_time,operations,profile,resources"
