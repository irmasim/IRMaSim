from irmasim.workload_manager.Backfill import Backfill
from irmasim.Options import Options
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from irmasim.Simulator import Simulator

class CartasanBackfill(Backfill):
    def __init__(self, simulator: 'Simulator'):
        super().__init__(simulator) # Call Backfill constructor
        options = Options().get()

        if 'algorithm' not in options['workload_manager']:
            self.algorithm = 'SAF'
        else:
            self.algorithm = options["workload_manager"]["algorithm"]

        algorithm = {
            'SPF': lambda job: job.req_time, # Smallest Estimated Processing Time First
            'SQF': lambda job: job.ntasks, # Smallest Resource Requirement First
            'SAF': lambda job: job.req_time * job.ntasks  # Smalles Estimated "Area" First
        }

        self.threshold = 4
        self.algorithm_sort_key = algorithm[options["workload_manager"]["algorithm"]]

        print("Using Cartasan workload manager") 
        print(f"Algorithm: {options["workload_manager"]["algorithm"]}")

    def order_pending_jobs(self):
        self.pending_jobs.sort(key=lambda job: job.submit_time 
                               if (self.simulator.simulation_time - job.submit_time) >= self.threshold 
                               else self.algorithm_sort_key(job) + self.simulator.simulation_time)

