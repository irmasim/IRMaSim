"""
Backfilling Workload Manager for heterogeneous Platforms
"""

from irmasim.Job import Job
import logging

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from irmasim.Simulator import Simulator

class BackfillingWorkloadManager():

    """
        Attributes:
            simulator:
                El simulador encargado de realizar toda la ejecución
            options:
                Parametros de configuración introducidos para la simulación
    """

    def __init__(self, options: dict, simulator: 'Simulator') -> None:

        self.simulator = simulator
        self.options = options

        logging.basicConfig(filename="info.log", level=getattr(logging, options['log_level']))


    # Trigger ejecutado cuando se hace el submit de un nuevo Job
    def onJobSubmission(self, job: Job) -> None:
        logging.debug('Job arrived: %s %s %s %s %s %s', job.id, job.req_time, job.req_ops, job.mem, job.mem_vol, job.estimated_execution_time)


    #Trigger ejecutado cuando un Job finaliza su ejecución
    def onJobCompletion(self, job: Job) -> None:
        self.simulator.resource_manager.update_state(job, list(job.allocation), 'FREE', self.simulator.simulation_time)
        self.simulator.job_scheduler.nb_active_jobs -= 1
        self.simulator.job_scheduler.nb_completed_jobs += 1

    # Trigger ejecutado cuando no quedan mas eventos en cada paso de la simulación
    # Cuando no hay mas eventos para el time step, el simulador se encarga de realizar el scheduling de los Jobs
    def onNoMoreEvents(self) -> None:
        self.schedule_jobs()

    # Trigger ejecutado cuando finaliza la simulación
    def onSimulationEnds(self) -> None:
        with open('{0}/makespans.log'.format(self.options['output_dir']), 'a+') as out_f:
            out_f.write(f'{self.simulator.simulation_time}\n')

    # Mapeo los trabajos pendientes en recursos disponibles
    def schedule_jobs(self) -> None:
        scheduled_jobs = []
        serviceable = True

        print("Time-Step:", self.simulator.simulation_time)
        self.simulator.job_scheduler.see_pending_jobs()

        while self.simulator.job_scheduler.nb_pending_jobs and serviceable:
            job = self.simulator.job_scheduler.peek_job()
            print("Escojo trabajo", job.id)
            resources = self.simulator.resource_manager.get_resources(job, self.simulator.simulation_time)
            if resources:
                job.allocation = resources
                scheduled_jobs.append(job)
                self.simulator.job_scheduler.remove_job()
            else:
                print("Job", job.id, "no tiene cores suficientes")

                resources_spent_time_step = 0
                for job in scheduled_jobs:
                    resources_spent_time_step += job.resources
                if resources_spent_time_step >= job.resources - self.simulator.resource_manager.available_resources():
                    serviceable = False
                else:
                    # Calcular el init time de acuerdo a los recursos
                    self.backfilling_gap = self.simulator.find_init_time(job.resources)
                    print("El backfilling gap es:", self.backfilling_gap)

                    i = 1
                    longitud = self.simulator.job_scheduler.nb_pending_jobs
                    while i < longitud:
                        possible_job = self.simulator.job_scheduler.get_N_pending_job(i)
                        if possible_job.estimated_execution_time + self.simulator.simulation_time < self.backfilling_gap:
                            possible_resources = self.simulator.resource_manager.get_resources(possible_job, self.simulator.simulation_time)
                            if possible_resources:
                                print("Se produce backfilling de Job:", possible_job.id)
                                possible_job.allocation = possible_resources
                                scheduled_jobs.append(possible_job)
                                self.simulator.job_scheduler.remove_job()
                                longitud = self.simulator.job_scheduler.nb_pending_jobs
                                i = i - 1
                        i += 1
                    serviceable = False
        
        if scheduled_jobs:
            self.simulator.job_scheduler.nb_active_jobs += len(scheduled_jobs)
            for job in scheduled_jobs:
                job.update_estimated_finish_time(self.simulator.simulation_time)
            self.simulator.job_scheduler.run_jobs(scheduled_jobs, self.simulator.simulation_time)
