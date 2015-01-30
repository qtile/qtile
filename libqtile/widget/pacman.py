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

import subprocess


class Pacman(base.ThreadedPollText):
    """
    Shows number of available updates.
    Needs the pacman package manager installed. So will only work in Arch Linux installation.
    """
    defaults = [
        ('unavailable', 'ffffff', 'Unavailable Color - no updates.'),
        ('execute', None, 'Command to execute on click'),
        ('update_interval', 60, "The update interval."),
    ]

    def __init__(self, **config):
        base.ThreadedPollText.__init__(self, **config)
        self.add_defaults(Pacman.defaults)

    def draw(self):
        if self.text == '0':
            self.layout.colour = self.unavailable
        else:
            self.layout.colour = self.foreground
        base.ThreadedPollText.draw(self)

    def poll(self):
        pacman = subprocess.Popen(['checkupdates'], stdout=subprocess.PIPE)
        return str(len(pacman.stdout.readlines()))

    def button_press(self, x, y, button):
        base.ThreadedPollText.button_press(self, x, y, button)
        if button == 1 and self.execute is not None:
            subprocess.Popen([self.execute], shell=True)
