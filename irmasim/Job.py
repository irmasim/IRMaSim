class Job:


    def __init__(self, id: int, name : str,subtime : float, resources: int, profile : dict, type : str):
        self.id = id
        self.name = name
        self.type = type
        self.profile = profile
        self.subtime = subtime
        self.resources = resources
        self.req_ops = profile['req_ops']
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
