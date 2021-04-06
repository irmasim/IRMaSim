import json

class Statistics:

    def __init__(self, options):
        self.energy = []
        self.edp = []
        self.latest_energy = []
        self.latest_edp = []
        self.options = options

    def calculate_energy_and_edp(self, core_pool : list, diff_time : float, all_jobs_scheduler = False):
        total_power = round(sum([core.state['current_power'] for core in core_pool]),9)
        self.energy.append(total_power * diff_time)
        self.edp.append(round(total_power * (diff_time ** 2),9))
        if all_jobs_scheduler:
            self.latest_energy.append(self.energy[-1])
            self.latest_edp.append(self.edp[-1])

    def write_results(self, time):
        with open('{0}/statistics.json'.format(self.options['output_dir']), 'w') as out_f:
            data = {
                "Energy_Consumed (Julios)" : sum(self.energy),
                "EDP (Julios*seconds)" : sum(self.edp),
                "Makespan (seconds)": time
            }
            json.dump(data, out_f, indent=4)

