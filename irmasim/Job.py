import math 
class Job:

    def __init__(self, job_id : int, name : str, job_type : int, subtime : float, resources : int, profile : dict, type : str):

        self.job_id = job_id
        self.name = name
        self.job_type = job_type
        self.subtime = subtime
        self.resources = resources
        self.profile = profile
        self.type = type

        self.req_ops = math.ceil(profile['req_ops'] / profile['ipc'])
        self.ipc = profile['ipc']
        self.req_time = profile['req_time']
        self.mem = profile['mem']
        self.mem_vol = profile['mem_vol']


        self.allocation = []
        self.core_finish = []



    def is_job_finished(self) -> bool:
        return len(self.core_finish) == len(self.allocation)

    def __lt__(self, other):
        return self.subtime < other.subtime

    def __eq__(self, other):
        if other == None:
            return False
        return self.id == other.id
