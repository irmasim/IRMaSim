from irmasim.Job import Job


class Task:

    def __init__(self, job: Job, resource: list, ops: float, opc: float, memory: float, memory_volume: float):
        self.job = job
        self.resource = resource
        self.ops = ops
        self.opc = opc
        self.memory = memory
        self.memory_volume = memory_volume
