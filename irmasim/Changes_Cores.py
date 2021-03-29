class ChangesCores:
    """
    Class which is use to represent and save changes in the p-states of cores

Attributes:
    num_cores (int):
        id of core in HDeepRM.
    timePStates (list(tuples)):
        The tuples is composed of two floats:
            | time (float):
                Time when core p-state changes
            | power (float):
                Power of core when p-state changes

"""

    def __init__(self, num_core, time, power) -> None:
        self.num_core: int = num_core
        self.timePStates: list = [(time, power)]

    def add_change(self, time, power) -> None:
        """
        Add one change of state
        :param time: time of the change
        :param power: power of core
        :return:
        """
        self.timePStates.append((time, power))

    def __str__(self) -> str:
        show = ""
        for i in self.timePStates:
            show = show + "(" + str(i[0]) + "," + str(i[1]) + ").  "
        return show
