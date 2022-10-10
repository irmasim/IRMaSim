from irmasim.platform.BasicProcessor import BasicProcessor


class Processor (BasicProcessor):

    def __init__(self, id: str, config: dict):
        super(Processor, self).__init__(id=id, config=config)
        self.requested_memory_bandwidth = 0.0
        self.mops_per_core = 0

    def schedule(self, tasks: list):
        super().schedule(tasks)
        self.update_speedup()

    def advance(self, delta_time: float):
        super().advance(delta_time)
        self.update_speedup()

    def reap(self, tasks: list):
        super().reap(tasks)
        self.update_speedup()

    def get_joules(self, delta_time: float):
        task_count = sum([(1) for core in self.children if core.task != None and core.task.ops > 0.0])
        if task_count == 0:
            return sum([(core.min_power*core.static_power) for core in self.children]) * delta_time
        else:
            return (sum([core.dynamic_power for core in self.children if core.task != None]) +
                    sum([core.static_power for core in self.children])) * delta_time

    def update_speedup(self):

        def ss(x):
            if x < 0:
                return 1
            elif x > 1:
                return 0
            else:
                return (1 - x * x * x * (x * (x * 6 - 15) + 10))

        def d(y, n):
            aux = (y - (core.da - n) * core.db) / (core.dc - n * core.dd)
            aux = ss(aux)
            return aux * (n * 0.6 / (1 + n * 0.6)) + 1 / (1 + n * 0.6)

        def perf(x, y, n):
            if x < core.c:
                return 1
            elif x > ((d(y, n) + core.b * core.c - 1) / core.b):
                return d(y, n)
            else:
                return core.b * (x - core.c) + 1


        self.requested_memory_bandwidth = sum([core.requested_memory_bandwidth for core in self.children])
        task_count = sum([(1) for core in self.children if core.task != None and core.task.ops > 0.0])
        for core in self.children:
            core.speedup = round(perf(self.requested_memory_bandwidth, core.requested_memory_bandwidth, task_count - 1), 9)


