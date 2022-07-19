import math
class Job:


    def __init__(self, id: int, name : str,subtime : float, resources: int, profile : dict, type : str, estimated_execution_time : float):
        self.id = id
        self.name = name
        self.type = type
        self.profile = profile
        self.subtime = subtime
        self.resources = resources
        self.req_ops = math.ceil(profile['req_ops'] / profile['ipc'])
        self.ipc = profile['ipc']
        self.req_time = profile['req_time']
        self.mem = profile['mem']
        self.mem_vol = profile['mem_vol']
        self.allocation = []
        self.core_finish = []
        self.estimated_execution_time = estimated_execution_time
        self.estimated_finish_time = 0

    def is_job_finished(self) -> bool:
        return len(self.core_finish) == len(self.allocation)

    def __lt__(self, other):
        return self.subtime < other.subtime

    def __eq__(self, other):
        if other == None:
            return False
        return self.id == other.id

    def update_estimated_finish_time(self, simulation_time: int) -> None:
        self.estimated_finish_time = self.estimated_execution_time + simulation_time
