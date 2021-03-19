class Job:


    def __init__(self, id: int, type: str, profile : str,
                 req_ops: int, ipc:float, req_time: float,
                 mem: float, mem_vol: float, subtime : float,
                 resources: int):
        self.type = type
        self.profile = profile
        self.req_ops = req_ops
        self.ipc = ipc
        self.req_time = req_time
        self.mem = mem
        self.mem_vol = mem_vol
        self.subtime = subtime
        self.resources = resources
        self.id = id
        self.last_update = None
        self.remaining_ops = -1
        self.cores = None

    def core_selection(self, cores: list):
        self.cores = cores

    def __lt__(self, other):
        return self.subtime < other.subtime

    def __eq__(self, other):
        return self.id == other.id