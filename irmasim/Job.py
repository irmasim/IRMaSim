import math
from irmasim.Task import Task


class Job:

    def __init__(self, id: int, name: str, submit_time: float, nodes: int, ntasks: int, ntasks_per_node: int, req_ops : int, ipc : float, req_time : float, req_energy : int, mem : int, mem_vol : float):
        self.tasks = None
        self.id = id
        self.rand = 0
        self.name = str(name)
        self.type = id
        self.profile = None
        self.submit_time = submit_time
        self.start_time = math.inf
        self.finish_time = 0.0
        if nodes <= 0:
            raise Exception(f"Job {id} must have nodes > 0")
        self.nodes = nodes
        if ntasks <= 0:
            raise Exception(f"Job {id} must have ntasks > 0")
        self.ntasks = ntasks
        if ntasks_per_node <= 0:
            raise Exception(f"Job {id} must have ntasks_per_node > 0")
        self.ntasks_per_node = ntasks_per_node 
        self.ops = math.ceil(req_ops / ipc)
        self.opc = ipc
        self.req_time = req_time
        self.req_energy = req_energy
        self.memory = mem
        self.memory_vol = mem_vol
        self.generate_tasks()

    @classmethod
    def from_profile(klass, id: int, name: str, submit_time: float, nodes: int, ntasks: int, ntasks_per_node: int, profile: dict, type: str):
        if 'req_energy' in profile:
            req_energy = profile['req_energy']
        else:
            req_energy = 0
        if 'ipc' in profile:
           ipc = profile['ipc']
        else:
           ipc = 1.0
        if 'mem_vol' in profile:
            mem_vol = profile['mem_vol']
        else:
            mem_vol = 1.0
        if 'mem' in profile:
            mem = profile['mem']
        else:
            mem = 0
        self=klass(id,name,submit_time, nodes, ntasks, ntasks_per_node, profile['req_ops'], ipc,
                   profile['req_time'], req_energy, mem, mem_vol)
        self.type = type
        self.profile = profile
        return self
    
    def is_job_finished(self):
        return sum([1 for task in self.tasks if task.ops > 0.0]) == 0

    def generate_tasks(self):
        self.tasks = []
        for task in range(self.ntasks):
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

    def task_strs(self):
        task_id = 0 
        task_strings = []
        for task in self.tasks:
            task_strings.append(",".join(map(lambda x: str(x), [".".join([self.name,str(task_id)]),
                self.req_time,self.ntasks,self.memory,self.submit_time,self.start_time, self.finish_time,
                task.execution_time, self.ops, self.memory_vol, self.type,
                task.resource == None and "None" or ".".join(task.resource)])))
            task_id += 1
        return task_strings

    def __str__(self):
        task_strings = self.task_strs()
        return "\n".join(task_strings)

    @classmethod
    def header(klass):
        return "id,req_time,ntasks,mem,submit_time,start_time,finish_time,execution_time,operations,mem_vol,profile,resources"
