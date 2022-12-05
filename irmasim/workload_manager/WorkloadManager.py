from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from irmasim.Simulator import Simulator


class WorkloadManager:

    def __init__(self, simulator: 'Simulator'):
        self.simulator = simulator

    def on_job_submission(self, jobs: list):
        pass

    def on_job_completion(self, jobs: list):
        pass

    def schedule_next_job(self):
        return False

    def on_end_step(self):
        pass

    def on_end_trajectory(self):
        pass

    def on_end_simulation(self):
        pass

