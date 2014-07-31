# -*- coding:utf-8 -*-
#
# Copyright (C) 2013, Roger Duran <rogerduran@gmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

import os
import base

class DF(base.ThreadedPollText):
    """
    Disk Free Widget

    By default the widget only displays if the space is less than warn_space
    """
    defaults = [
        ('partition', '/', 'the partition to check space'),
        ('warn_color', 'ff0000', 'Warning color'),
        ('warn_space', 2, 'Warning space in scale defined by the ``measure`` option.'),
        ('visible_on_warn', True, 'Only display if warning'),
        ('measure', "G", "Measurement (G, M, B)"),
        ('format', '{p} ({uf}{m})',
                    'String format (p: partition, s: size, '\
                    'f: free space, uf: user free space, m: measure)'),
        ('update_interval', 60, 'The update inteval.'),
    ]

    measures = {"G": 1024*1024*1024,
                "M": 1024*1024,
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

        size = statvfs.f_frsize * statvfs.f_blocks / self.calc
        free = statvfs.f_frsize * statvfs.f_bfree / self.calc
        self.user_free = statvfs.f_frsize * statvfs.f_bavail / self.calc

        if self.visible_on_warn and self.user_free >= self.warn_space:
            text = ""
        else:
            text = self.format.format(p=self.partition, s=size, f=free,
                    uf=self.user_free, m=self.measure)

        return text
