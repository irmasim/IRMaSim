

class Statistics:

    def __init__(self):
        self.energy = []
        self.edp = []

    def calculate_energy_and_edp(self, core_pool : list, diff_time : float):
        total_power = sum([core.state['current_power'] for core in core_pool])
        self.energy.append(total_power * diff_time)
        self.edp.append(total_power * (diff_time ** 2))

