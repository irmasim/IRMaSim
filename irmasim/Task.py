from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from irmasim.Job import Job


class Task:

    def __init__(self, job: 'Job', ops: float, opc: float, memory: float, memory_volume: float):
        self.job = job
        self.resource = None
        self.ops = ops
        self.opc = opc
        self.memory = memory
        self.memory_volume = memory_volume

    def allocate(self, resource: list):
        self.resource = resource

    def __str__(self):
        return ",".join(map(lambda x: str(x), [self.job.id, self.resource, self.ops]))
