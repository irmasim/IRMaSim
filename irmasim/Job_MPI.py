import math
from irmasim.Job import Job
class Job_MPI(Job):

    def __init__(self, job_id : int, name : str, job_type : int, subtime : float, resources: int, profile : dict, type : str, num_nodes : int, tasks : [], comm_vol : float, t_compute : float):

        # atributos generales heredados

        super().__init__(job_id, name, job_type, subtime, resources, profile, type)


        # atributos especificos

        self.num_nodes = num_nodes
        self.tasks = tasks
        self.comm_vol = comm_vol
        self.profile = profile
        self.t_compute = t_compute
