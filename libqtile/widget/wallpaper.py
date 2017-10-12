# Copyright (c) 2015 Muhammed Abuali
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
#
# To use this widget, you will need to install feh wallpaper changer

import os
import subprocess
import random
from . import base
from .. import bar
from libqtile.log_utils import logger


class Wallpaper(base._TextBox):
    defaults = [
        ("directory", "~/Pictures/wallpapers/", "Wallpaper Directory"),
        ("wallpaper", None, "Wallpaper"),
        ("wallpaper_command", None, "Wallpaper command"),
        ("random_selection", False, "If set, use random initial wallpaper and "
         "randomly cycle through the wallpapers."),
        ("label", None, "Use a fixed label instead of image name."),
        ("one_screen", False, "Treat the whole X display as one screen when setting wallpapers (does not work if wallpaper_command is set)."),
    ]

    def __init__(self, **config):
        base._TextBox.__init__(self, 'empty', width=bar.CALCULATED, **config)
        self.add_defaults(Wallpaper.defaults)
        self.index = 0
        self.images = []
        self.get_wallpapers()
        if self.random_selection: # Random selection after reading all files
            self.index = random.randint(0, len(self.images) - 1)
        self.set_wallpaper()

    def get_path(self, file):
        return os.path.join(os.path.expanduser(self.directory), file)

    def get_wallpapers(self):
        try:
            # get path of all files in the directory
            self.images = list(
                filter(os.path.isfile,
                       map(self.get_path,
                           os.listdir(self.directory))))
        except IOError as e:
            logger.exception("I/O error(%s): %s", e.errno, e.strerror)

    def set_wallpaper(self):
        if len(self.images) == 0:
            if self.wallpaper is None:
                self.text = "empty"
                return
            else:
                self.images.append(self.wallpaper)
        cur_image = self.images[self.index]
        if self.label is None:
            self.text = os.path.basename(cur_image)
        else:
            self.text = self.label
        if self.wallpaper_command:
            self.wallpaper_command.append(cur_image)
            subprocess.call(self.wallpaper_command)
            return
        command = [
            'feh',
            '--bg-fill',
            cur_image
        ]
        if self.one_screen:
            command.append("--no-xinerama")
        subprocess.call(command)

    def button_press(self, x, y, button):
        if button == 1:
            if self.random_selection:
                self.index = random.randint(0, len(self.images) - 1)
            else:
                self.index += 1
                self.index %= len(self.images)
            self.set_wallpaper()
            self.draw()
