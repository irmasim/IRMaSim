import math
class Task:


    def __init__(self, id_task : int, job_id : int, name : str, subtime : float, resources : int, comm_vol : float, t_compute : float, profile_task : dict, type : str, tasks : list):

        self.id_task = id_task
        self.job_id = job_id
        self.profile_task = profile_task
        self.type = type
        self.subtime = subtime
        self.job_type = 2
        self.comm_vol = comm_vol
        self.t_compute = t_compute
        self.tasks = tasks
        self.resources = resources
        self.name = name
        self.pending_tasks = len(tasks)


        self.req_ops = math.ceil(profile_task['req_ops'] / profile_task['ipc'])
        self.ipc = profile_task['ipc']
        self.req_time = profile_task['req_time']
        self.mem = profile_task['mem']
        self.mem_vol = profile_task['mem_vol']

        self.allocation = []
        self.core_finish = []

    def task_executed(self):
        self.pending_tasks = self.pending_tasks - 1


    def is_job_finished(self) -> bool:
        return len(self.core_finish) == len(self.allocation)


    def __lt__ (self, other):
        return self.subtime < other.subtime

    def __eq__(self, other):
        if other == None:
            return False
        return self.id_task == other.id_task
    
    def __getitem__(self, key):
        return key
