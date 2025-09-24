import psutil

from libqtile.widget import base


class CPU(base.InLoopPollText):
    """
    A simple widget to display CPU load and frequency.

    Widget requirements: psutil_.

    .. _psutil: https://pypi.org/project/psutil/
    """

    defaults = [
        ("update_interval", 1.0, "Update interval for the CPU widget"),
        (
            "format",
            "CPU {freq_current}GHz {load_percent}%",
            "CPU display format",
        ),
    ]

    def __init__(self, **config):
        super().__init__("", **config)
        self.add_defaults(CPU.defaults)

    def poll(self):
        variables = dict()

        variables["load_percent"] = round(psutil.cpu_percent(), 1)
        freq = psutil.cpu_freq()
        if psutil.__version__ == "5.9.0":
            variables["freq_current"] = round(freq.current, 1)
        else:
            variables["freq_current"] = round(freq.current / 1000, 1)
        variables["freq_max"] = round(freq.max / 1000, 1)
        variables["freq_min"] = round(freq.min / 1000, 1)

        return self.format.format(**variables)
