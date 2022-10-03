import math
class Job:


    def __init__(self, id: int, name : str,subtime : float, resources: int, profile : dict, type : str):
        self.id = id
        self.name = name
        self.type = type
        self.profile = profile
        self.subtime = subtime
        self.resources = resources
        self.req_ops = math.ceil(profile['req_ops'] / profile['ipc'])
        self.ipc = profile['ipc']
        self.req_time = profile['req_time']
        self.memory = profile['mem']
        self.mem_vol = profile['mem_vol']
        self.allocation = []
        self.core_finish = []
        self.tasks = []

    def is_job_finished(self):
        return sum([(1) for task in self.tasks if task.ops > 0.0]) == 0


    def __lt__(self, other):
        return self.subtime < other.subtime

    def __eq__(self, other):
        if other == None:
            return False
        return self.id == other.id
