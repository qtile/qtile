# -*- coding:utf-8 -*-
#
# Copyright (C) 2012, Maximilian Köhl <linuxmaxi@googlemail.com>
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

import base

from .. import bar, manager

import subprocess

class Pacman(base._TextBox):
    """
    Shows number of available updates.
    """
    defaults = manager.Defaults(
        ('font', 'Arial', 'Clock font'),
        ('fontsize', None, 'Updates widget font size. Calculated if None.'),
        ('padding', None, 'Updates widget padding. Calculated if None.'),
        ('background', '000000', 'Background Color'),
        ('foreground', 'ff0000', 'Foreground Color'),
        ('unavailable', 'ffffff', 'Unavailable Color - no updates.')
    )
    def __init__(self, interval=60, **config):
        base._TextBox.__init__(self, '', bar.CALCULATED, **config)
        self.interval = interval
        self.text = str(self.updates())
        

    def _configure(self, qtile, bar):
        base._TextBox._configure(self, qtile, bar)
        self.timeout_add(self.interval, self.update)
    
    def draw(self):
        if self.text == '0':
            self.layout.colour = self.unavailable
        else:
            self.layout.colour = self.foreground
        base._TextBox.draw(self)
    
    def updates(self):
        pacman = subprocess.Popen(['pacman', '-Qu'], stdout=subprocess.PIPE)
        return len(pacman.stdout.readlines())
    
    def update(self):
        updates = str(self.updates())
        if self.text != updates:
            self.text = updates
            self.bar.draw()
        return True
