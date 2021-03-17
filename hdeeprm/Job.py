
import resource

class Job:


    def __init__(self, id: int, type: str, profile : str,
                 req_ops: int, ipc:float, req_time: float,
                 mem: float, mem_vol: float, subtime : float,
                 res: int):
        self.type = type
        self.profile = profile
        self.req_ops = req_ops
        self.ipc = ipc
        self.req_time = req_time
        self.mem = mem
        self.mem_vol = mem_vol
        self.subtime = subtime
        self.res = res
        self.id = id
        self.core = None


    def core_selection(self, core: resource.Core):
        self.core = core


    def __lt__(self, other):
        return self.subtime < other.subtime