# -*- coding: utf-8 -*-
# Copyright (c) 2015 Jörg Thalheim (Mic92)
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
import psutil

from libqtile.widget import base

__all__ = ["Memory"]


class Memory(base.ThreadPoolText):
    """Displays memory/swap usage

    MemUsed: Returns memory in use
    MemTotal: Returns total amount of memory
    MemFree: Returns amount of memory free
    MemPercent: Returns memory in use as a percentage
    Buffers: Returns buffer amount
    Active: Returns active memory
    Inactive: Returns inactive memory
    Shmem: Returns shared memory
    SwapTotal: Returns total amount of swap
    SwapFree: Returns amount of swap free
    SwapUsed: Returns amount of swap in use
    SwapPercent: Returns swap in use as a percentage


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
