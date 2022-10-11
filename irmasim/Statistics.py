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

    def write_results(self, time : float, finished_jobs : list):
        with open('{0}/statistics.json'.format(self.options['output_dir']), 'w') as out_f:
            data = {
                "Energy_Consumed (J)" : sum(self.energy),
                "EDP (J*seconds)" : sum(self.edp),
                "Makespan (seconds)": time
            }
            json.dump(data, out_f, indent=4)
        with open('{0}/jobs.log'.format(self.options['output_dir']), 'w') as out_f:
            jobs = "Name, subtime ,start_runing, finish, execution_time, instructions, profile, cores\n"
            for i in sorted(finished_jobs, key= lambda x: x.name):
                jobs += i.name +"," + str(i.submit_time) + "," + str(i.start_running) + "," + str(i.finish) + "," + str(i.finish - i.start_running) + "," + \
                        str(i.req_ops) +"," + str(i.type) +"," + str(i.core_finish) +"\n"
            out_f.write(jobs)