from itertools import cycle

from psutil import getloadavg

from libqtile.command.base import expose_command
from libqtile.widget import base


class Load(base.InLoopPollText):
    """
    A small widget to show the load averages of the system.
    Depends on psutil.
    """

    defaults = [
        ("update_interval", 1.0, "The update interval for the widget"),
        ("format", "Load({time}):{load:.2f}", "The format in which to display the results."),
    ]
    times = ["1m", "5m", "15m"]

    def __init__(self, **config):
        super().__init__("", **config)
        self.add_defaults(Load.defaults)
        self.add_callbacks({"Button1": self.next_load})
        self.cycled_times = cycle(Load.times)
        self.set_time()

    def set_time(self):
        self.time = next(self.cycled_times)

    @expose_command()
    def next_load(self):
        self.set_time()
        self.update(self.poll())

    def poll(self):
        loads = {}
        (
            loads["1m"],
            loads["5m"],
            loads["15m"],
        ) = getloadavg()  # Gets the load averages as a dictionary.
        load = loads[self.time]
        return self.format.format(time=self.time, load=load)
