class Job:


    def __init__(self, id: int, subtime : float, resources: int, profile : dict):
        self.id = id
        self.profile = profile
        self.subtime = subtime
        self.resources = resources
        self.req_ops = profile['req_ops']
        self.ipc = profile['ipc']
        self.req_time = profile['req_time']
        self.mem = profile['mem']
        self.mem_vol = profile['mem_vol']
        self.type = profile['type']
        self.last_update = subtime
        self.remaining_ops = -1
        self.allocation = None

    def __lt__(self, other):
        return self.subtime < other.subtime

    def __eq__(self, other):
        return self.id == other.id