import math
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
        self.execution_time = 0

    def allocate(self, resource: list):
        self.resource = resource

    def advance(self, delta_time: float, delta_ops: float):
        self.ops -= math.floor(delta_ops)
        if self.ops >= 0:
            self.execution_time += delta_time

    def __str__(self):
        return ",".join(map(lambda x: str(x), [self.job.id, self.resource, self.ops]))
