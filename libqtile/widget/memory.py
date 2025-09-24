import psutil

from libqtile.widget import base

__all__ = ["Memory"]


class Memory(base.InLoopPollText):
    """Display memory/swap usage.

    The following fields are available in the `format` string:

    - ``MemUsed``: Memory in use.
    - ``MemTotal``: Total amount of memory.
    - ``MemFree``: Amount of memory free.
    - ``Available``: Amount of memory available.
    - ``NotAvailable``: Equal to ``MemTotal`` - ``MemAvailable``
    - ``MemPercent``: Memory in use as a percentage.
    - ``Buffers``: Buffer amount.
    - ``Active``: Active memory.
    - ``Inactive``: Inactive memory.
    - ``Shmem``: Shared memory.
    - ``SwapTotal``: Total amount of swap.
    - ``SwapFree``: Amount of swap free.
    - ``SwapUsed``: Amount of swap in use.
    - ``SwapPercent``: Swap in use as a percentage.
    - ``mm``: Measure unit for memory.
    - ``ms``: Measure unit for swap.

    Widget requirements: psutil_.

    .. _psutil: https://pypi.org/project/psutil/

    """

    defaults = [
        ("format", "{MemUsed: .0f}{mm}/{MemTotal: .0f}{mm}", "Formatting for field names."),
        ("update_interval", 1.0, "Update interval for the Memory"),
        ("measure_mem", "M", "Measurement for Memory (G, M, K, B)"),
        ("measure_swap", "M", "Measurement for Swap (G, M, K, B)"),
    ]

    measures = {"G": 1024 * 1024 * 1024, "M": 1024 * 1024, "K": 1024, "B": 1}

    def __init__(self, **config):
        super().__init__("", **config)
        self.add_defaults(Memory.defaults)
        self.calc_mem = self.measures[self.measure_mem]
        self.calc_swap = self.measures[self.measure_swap]

    def poll(self):
        mem = psutil.virtual_memory()
        swap = psutil.swap_memory()
        val = {}
        val["MemUsed"] = mem.used / self.calc_mem
        val["MemTotal"] = mem.total / self.calc_mem
        val["MemFree"] = mem.free / self.calc_mem
        val["Available"] = mem.available / self.calc_mem
        val["NotAvailable"] = (mem.total - mem.available) / self.calc_mem
        val["MemPercent"] = mem.percent
        val["Buffers"] = mem.buffers / self.calc_mem
        val["Active"] = mem.active / self.calc_mem
        val["Inactive"] = mem.inactive / self.calc_mem
        val["Shmem"] = mem.shared / self.calc_mem
        val["SwapTotal"] = swap.total / self.calc_swap
        val["SwapFree"] = swap.free / self.calc_swap
        val["SwapUsed"] = swap.used / self.calc_swap
        val["SwapPercent"] = swap.percent
        val["mm"] = self.measure_mem
        val["ms"] = self.measure_swap

        return self.format.format(**val)
