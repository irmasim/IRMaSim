import math
from irmasim.Task import Task


class Job:

    def __init__(self, id: int, name: str, submit_time: float, resources: int, req_ops : int, ipc : float, req_time : float, mem : int, mem_vol : float):
        self.tasks = None
        self.id = id
        self.name = name
        self.type = id
        self.profile = None
        self.submit_time = submit_time
        self.start_time = math.inf
        self.finish_time = 0.0
        self.resources = resources
        self.ops = math.ceil(req_ops / ipc)
        self.opc = ipc
        self.req_time = req_time
        self.memory = mem
        self.memory_vol = mem_vol
        self.generate_tasks()

    @classmethod
    def from_profile(klass, id: int, name: str, submit_time: float, resources: int, profile: dict, type: str):
        self=klass(id,name,submit_time,resources, profile['req_ops'], profile['ipc'],
                   profile['req_time'], profile['mem'], profile['mem_vol'])
        self.type = type
        self.profile = profile
        return self
    
    def is_job_finished(self):
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
        task_id = 0 
        task_strings = []
        for task in self.tasks:
            task_strings.append(",".join(map(lambda x: str(x), [".".join([str(self.id),str(task_id)]), self.submit_time, self.start_time, self.finish_time,
                                                task.execution_time, self.ops, self.type, task.resource == None and "None" or ".".join(task.resource)])))
            task_id += 1
        return "\n".join(task_strings)

    @classmethod
    def header(klass):
        return "id,submit_time,start_time,finish_time,execution_time,operations,profile,resources"
