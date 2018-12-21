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
from __future__ import division

import psutil

from libqtile.widget import base

__all__ = [
    'Memory',
    'Swap',
]


def get_meminfo():
    mem = psutil.virtual_memory()
    swap = psutil.swap_memory()
    val = {}
    val['MemUsed'] = mem.used // 1024 // 1024
    val['MemTotal'] = mem.total // 1024 // 1024
    val['MemFree'] = mem.free // 1024 // 1024
    val['Buffers'] = mem.buffers // 1024 // 1024
    val['Active'] = mem.active // 1024 // 1024
    val['Inactive'] = mem.inactive // 1024 // 1024
    val['Shmem'] = mem.shared // 1024 // 1024
    val['SwapTotal'] = swap.total // 1024 // 1024
    val['Swapfree'] = swap.free // 1024 // 1024
    val['SwapUsed'] = swap.used // 1024 // 1024

    return val


class Swap(base.ThreadedPollText):
    """Displays memory usage"

    SwapTotal: Returns total amount of swap
    SwapFree: Returns amount of swap free
    SwapUsed: Returns amount of swap in use
"""
    orientations = base.ORIENTATION_HORIZONTAL
    defaults = [
        ("fmt", "{SwapUsed}M/{SwapTotal}M", "Formatting for field names.")
    ]

    def __init__(self, **config):
        super(Swap, self).__init__(**config)
        self.add_defaults(Swap.defaults)

    def poll(self):
        return self.fmt.format(**get_meminfo())


class Memory(base.ThreadedPollText):
    """Displays memory/swap usage

    MemUsed: Returns memory in use
    MemTotal: Returns total amount of memory
    MemFree: Returns amount of memory free
    Buffers: Returns buffer amount
    Active: Returns active memory
    Inactive: Returns inactive memory
    Shmem: Returns shared memory
"""
    orientations = base.ORIENTATION_HORIZONTAL
    defaults = [
        ("fmt", "{MemUsed}M/{MemTotal}M", "Formatting for field names.")
    ]

    def __init__(self, **config):
        super(Memory, self).__init__(**config)
        self.add_defaults(Memory.defaults)

    def poll(self):
        return self.fmt.format(**get_meminfo())
