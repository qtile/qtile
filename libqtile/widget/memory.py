# vim: tabstop=4 shiftwidth=4 expandtab
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
from libqtile.widget import base


def get_meminfo():
    val = {}
    with open('/proc/meminfo') as file:
        for line in file:
            key, tail = line.split(':')
            uv = tail.split()
            val[key] = int(uv[0]) // 1000
    val['MemUsed'] = val['MemTotal'] - val['MemFree']
    return val


class Memory(base.InLoopPollText):
    """Displays memory usage."""
    orientations = base.ORIENTATION_HORIZONTAL
    defaults = [
        ("fmt", "{MemUsed}M/{MemTotal}M", "see /proc/meminfo for field names")
    ]

    def __init__(self, **config):
        super(Memory, self).__init__(**config)
        self.add_defaults(Memory.defaults)

    def poll(self):
        return self.fmt.format(**get_meminfo())
