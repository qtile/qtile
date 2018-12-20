# -*- coding: utf-8 -*- # Copyright (c) 2015 Jörg Thalheim (Mic92)
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


def get_swapinfo():
    val = {}
    val['SwapUsed'] = int(psutil.swap_memory().used / 1024 / 1024)
    val['SwapTotal'] = int(psutil.swap_memory().total / 1024 / 1024)
    val['SwapFree'] = val['SwapTotal'] - val['SwapUsed']
    return val


class Swap(base.InLoopPollText):
    """Displays swap usage
SwapUsed: Returns swap used
SwapTotal: Returns total amount of swap space
SwapFree: Returns amount of swap free
"""
    orientations = base.ORIENTATION_HORIZONTAL
    defaults = [
        ("fmt", "{SwapUsed}M/{SwapTotal}M", "Format field names")
    ]

    def __init__(self, **config):
        super(Swap, self).__init__(**config)
        self.add_defaults(Swap.defaults)

    def poll(self):
        return self.fmt.format(**get_swapinfo())
