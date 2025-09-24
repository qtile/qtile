from libqtile.widget import base


class HDD(base.InLoopPollText):
    """
    Displays HDD usage in percent based on the number of milliseconds the device has been performing I/O operations.
    """

    defaults = [
        ("device", "sda", "Block device to monitor (e.g. sda)"),
        (
            "format",
            "HDD {HDDPercent}%",
            "HDD display format",
        ),
    ]

    def __init__(self, **config):
        super().__init__("", **config)
        self.add_defaults(HDD.defaults)
        self.path = f"/sys/block/{self.device}/stat"
        self._prev = 0

    def poll(self):
        variables = dict()
        # Field index 9 contains the number of milliseconds the device has been performing I/O operations
        with open(self.path) as f:
            io_ticks = int(f.read().split()[9])

        variables["HDDPercent"] = round(
            max(min(((io_ticks - self._prev) / self.update_interval) / 10, 100.0), 0.0), 1
        )

        self._prev = io_ticks

        return self.format.format(**variables)
