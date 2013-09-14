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

from .. import bar, obj

import subprocess


class Pacman(base._TextBox):
    """
    Shows number of available updates.
    """
    defaults = [('unavailable', 'ffffff', 'Unavailable Color - no updates.')]

    def __init__(self, execute=None, interval=60, **config):
        base._TextBox.__init__(self, '', obj.CALCULATED, **config)
        self.add_defaults(Pacman.defaults)
        self.interval = interval
        self.execute = execute
        self.text = str(self.updates())
        self.timeout_add(self.interval, self.update)

    def draw(self):
        if self.text == '0':
            self.layout.colour = self.unavailable
        else:
            self.layout.colour = self.foreground
        base._TextBox.draw(self)

    def updates(self):
        pacman = subprocess.Popen(['checkupdates'], stdout=subprocess.PIPE)
        return len(pacman.stdout.readlines())

    def update(self):
        if self.configured:
            updates = str(self.updates())
            if self.text != updates:
                self.text = updates
                self.bar.draw()
        return True

    def button_press(self, x, y, button):
        if button == 1 and self.execute is not None:
            subprocess.Popen([self.execute], shell=True)
