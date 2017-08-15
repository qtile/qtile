# -*- coding:utf-8 -*-
# Copyright (c) 2015, Roger Duran. All rights reserved.
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

import os

from . import base


class DF(base.ThreadedPollText):
    """Disk Free Widget

    By default the widget only displays if the space is less than warn_space.
    """
    orientations = base.ORIENTATION_HORIZONTAL
    defaults = [
        ('partition', '/', 'the partition to check space'),
        ('warn_color', 'ff0000', 'Warning color'),
        ('warn_space', 2, 'Warning space in scale defined by the ``measure`` option.'),
        ('visible_on_warn', True, 'Only display if warning'),
        ('measure', "G", "Measurement (G, M, B)"),
        ('format', '{p} ({uf}{m}|{r:.0f}%)',
            'String format (p: partition, s: size, '
            'f: free space, uf: user free space, m: measure, r: ratio (uf/s))'),
        ('update_interval', 60, 'The update interval.'),
    ]

    measures = {"G": 1024 * 1024 * 1024,
                "M": 1024 * 1024,
                "B": 1024}
    def __init__(self, **config):
        base.ThreadedPollText.__init__(self, **config)
        self.add_defaults(DF.defaults)
        self.user_free = 0
        self.calc = self.measures[self.measure]

    def draw(self):
        if self.user_free <= self.warn_space:
            self.layout.colour = self.warn_color
        else:
            self.layout.colour = self.foreground

        base.ThreadedPollText.draw(self)

    def poll(self):
        statvfs = os.statvfs(self.partition)

        size = statvfs.f_frsize * statvfs.f_blocks // self.calc
        free = statvfs.f_frsize * statvfs.f_bfree // self.calc
        self.user_free = statvfs.f_frsize * statvfs.f_bavail // self.calc

        if self.visible_on_warn and self.user_free >= self.warn_space:
            text = ""
        else:
            text = self.format.format(p=self.partition, s=size, f=free,
                    uf=self.user_free, m=self.measure,
                    r=(size - self.user_free) / size * 100)

        return text
