from irmasim.platform.BasicNode import BasicNode
from irmasim.Task import Task
import math


class Process:
    def __init__(self, node: 'Node', task: Task):
        self.node = node
        self.task = task
        self.requested_memory_bandwidth = task.memory_volume / \
                                          (task.ops / (self.node.gops * 1e9))
        self.speedup = 1

    def update_speedup(self):
        other=len(self.node.processes)-1
        all_bw=self.node.requested_memory_bandwidth*1e-3
        int_bw=self.requested_memory_bandwidth*1e-3

        ab = self.node.abb + other * self.node.aba
        aa = self.node.aab + other * self.node.aaa

        bb = self.node.bbb + other * self.node.bba
        ba = self.node.bab + other * self.node.baa

        ca = self.node.cab + other * self.node.caa
        cb = self.node.cbb + other * self.node.cba
        cc = self.node.ccb + other * self.node.cca

        db = self.node.dbb + other * self.node.dba
        da = self.node.dab + other * self.node.daa

        a = ab + int_bw * aa
        b = bb + int_bw * ba
        c = cc + int_bw * cb + int_bw**2 * ca
        d = db + int_bw * da

        self.speedup = b+(c-b)*math.exp(-math.exp(a*(all_bw-d)))*0.9

    def get_next_step(self):
            return self.task.ops / (self.node.gops * 1e9 * self.speedup)

    def advance(self, delta_time: float):
        self.task.advance(delta_time, self.node.gops * 1e9 * self.speedup * delta_time)

class Node (BasicNode):

    def __init__(self, id: list, config: dict):
        super(Node, self).__init__(id=id, config=config)
        self.processes = []
        self.gops = config['clock_rate']

        self.aaa = config['aaa']
        self.aab = config['aab']
        self.aba = config['aba']
        self.abb = config['abb']
        self.baa = config['baa']
        self.bab = config['bab']
        self.bba = config['bba']
        self.bbb = config['bbb']
        self.caa = config['caa']
        self.cab = config['cab']
        self.cba = config['cba']
        self.cbb = config['cbb']
        self.cca = config['cca']
        self.ccb = config['ccb']
        self.daa = config['daa']
        self.dab = config['dab']
        self.dba = config['dba']
        self.dbb = config['dbb']

        self.pidle = config['pidle']
        self.p00 = config['p00']
        self.p01 = config['p01']
        self.p02 = config['p02']
        self.p10 = config['p10']
        self.p11 = config['p11']
        self.p20 = config['p20']

        self.requested_memory_bandwidth = 0

    def schedule(self, task: Task, resource_id: list):
        process = Process(self,task)
        self.processes.append(process)
        self.requested_memory_bandwidth += process.requested_memory_bandwidth
        self.update_speedup()

    def get_next_step(self):
        if self.processes == []:
            return math.inf
        else:
            return min([process.get_next_step() for process in self.processes])

    def advance(self, delta_time: float):
        for process in self.processes:
            process.advance(delta_time)

    def reap(self, task: Task, resource_id: list):
        for process in self.processes:
            if process.task == task:
                self.processes.remove(process)
                self.requested_memory_bandwidth -= process.requested_memory_bandwidth
                break
        self.update_speedup()

    def update_speedup(self):
        for process in self.processes:
            process.update_speedup()
        
    def get_joules(self, delta_time: float):
        job_count = len(self.processes)
        if job_count == 0:
            return self.pidle*delta_time
        all_bw=self.requested_memory_bandwidth*1e-3
        p = self.p00 + \
            self.p10 * all_bw + self.p20 * all_bw**2 + \
            self.p01 * job_count + self.p02 * job_count**2 + \
            self.p11 * all_bw * job_count 
        return p*delta_time
