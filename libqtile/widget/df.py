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

from .. import bar

class DF(base._TextBox):
    """
    Disk Free Widget

    By default the widget only displays if the space is less than warn_space
    """
    defaults = [
        ('partition', '/', 'the partition to check space'),
        ('warn_color', 'ff0000', 'Warning color'),
        ('warn_space', 2, 'Warning space'),
        ('visible_on_warn', True, 'Only display if warning'),
        ('measure', "G", "Measurement (G, M, B)"),
        ('format', '{p} ({uf}{m})',
                    'String format (p: partition, s: size, '\
                    'f: free space, uf: user free space, m: measure)'),
    ]

    measures = {"G": 1024*1024*1024,
                "M": 1024*1024,
                "B": 1024}
    def __init__(self, interval=60, **config):
        base._TextBox.__init__(self, '', bar.CALCULATED, **config)
        self.add_defaults(DF.defaults)
        self.interval = interval
        self.user_free = 0
        self.calc = self.measures[self.measure]
        self.update()
        self.timeout_add(self.interval, self.update)

    def draw(self):
        if self.user_free <= self.warn_space:
            self.layout.colour = self.warn_color
        else:
            self.layout.colour = self.foreground

        base._TextBox.draw(self)

    def update(self):
        statvfs = os.statvfs(self.partition)

        size = statvfs.f_frsize * statvfs.f_blocks / self.calc
        free = statvfs.f_frsize * statvfs.f_bfree / self.calc
        self.user_free = statvfs.f_frsize * statvfs.f_bavail / self.calc

        if self.visible_on_warn and self.user_free >= self.warn_space:
            text = ""
        else:
            text = self.format.format(p=self.partition, s=size, f=free,
                    uf=self.user_free, m=self.measure)

        if self.text != text:
            self.text = text
            if self.configured:
                self.bar.draw()

        return True
