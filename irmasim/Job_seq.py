import math
from irmasim.Job import Job
class Job_seq(Job):


    def __init__(self, job_id : int, name : str, job_type : int, subtime : float, resources: int, profile : dict, type : str):

        # atributos heredados

        super().__init__(job_id, name, job_type, subtime, resources, profile, type)

        self.profile = profile
        self.type = type

        #TODO: self.tcpu

        #self.allocation = []
        #self.core_finish = []

        
    # metodo redefinido

    #def is_job_finished(self) -> bool:
        #return len(self.core_finish) == len(self.allocation)
    


    # metodos definidos en la clase padre

    #def __lt__(self, other):
    #    return self.subtime < other.subtime

    #def __eq__(self, other):
    #    if other == None:
    #        return False
    #    return self.id == other.id
