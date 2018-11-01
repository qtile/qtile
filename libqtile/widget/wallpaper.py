# Copyright (c) 2015 Muhammed Abuali
# Copyright (c) 2018 Valentijn van de Beek
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
import pathlib
import subprocess
import random

from libqtile.widget import base
from libqtile import bar
from libqtile.log_utils import logger

user_dir_path = os.path.expanduser("~/.config/user-dirs.dirs")
pictures_dir = "~/Pictures/wallpapers"
if os.path.exists(user_dir_path):
    with open(user_dir_path, 'r') as f:
        for line in f.read().split('\n'):
            if line[0] == '#' or line is None:
                continue
            key, value = line.split('=')
            if key == "XDG_PICTURES_DIR":
                pictures_dir = os.path.expandvars(value).replace('"', '')
                break


class Wallpaper(base.ThreadPoolText):
    """
    A simple wallpaper widget that can set the wallpaper and change it
    on an interval or if you press on the widget.
    """
    defaults = [
        ("wallpaper", "cycle", "the path to a wallpaper or the special value cycle or random"),
        ("directories", pictures_dir, "Either an absolute or relative path to directory or "
         "list of absolute or relative paths to directories. Relative paths are resolved "
         "to $XDG_PICTURES_DIR"),
        ("wallpaper_command", ('feh', '--bg-max'), "Wallpaper command"),
        ("label", None, "Use a fixed label instead of image name."),
        ("one_screen", False, "Treat the whole X display as one screen when setting wallpapers "),
        ("update_interval", None, "Update interval in seconds, if none, it won't update")
    ]

    def __init__(self, **config):
        base._TextBox.__init__(self, 'empty', width=bar.CALCULATED, **config)
        self.add_defaults(Wallpaper.defaults)
        self.images = []
        self.command, *self.args = self.wallpaper_command

        if self.one_screen:
            # Support other commands other than feh?
            self.wallpaper_command.append("--no-xinerama")

        self.cycle = self.wallpaper.lower() == "cycle"
        self.random = self.wallpaper.lower() == "random"

        if self.cycle or self.random:
            self.get_wallpapers()

        self.index = 0

    def poll(self):
        """
        Return the current wallpaper
        """
        return self.wallpaper

    def _get_wallpapers_in_directory(self, directory):
        """
        Add all the wallpapers in a given directory to the images list
        """
        if directory[0] not in ('~', '/'):
            directory = pictures_dir + directory

        path = pathlib.Path(directory).expanduser()

        for ext in ('jpg', 'png', 'jpeg'):
            self.images.extend([img for img in path.glob('**/*' + ext)])

    def get_wallpapers(self):
        # type: () -> None
        """
        Create a list of all the images in a given directory.
        """
        if type(self.directories) is str:
            self._get_wallpapers_in_directory(self.directories)

        for directory in self.directories:
            self._get_wallpapers_in_directory(directory)

    def set_wallpaper(self, *args):
        """
        Set the wallpaper either to given wallpaper or to one in a cycle.
        """
        # type: () -> None
        image = self.wallpaper

        if self.random or self.cycle:
            if self.random:
                self.index = random.randint(0, len(self.images) - 1)
            else:
                self.index += 1
                self.index %= len(self.images)

            image = str(self.images[self.index])
            print(image)

        if self.label is None:
            self.text = os.path.basename(image)
        else:
            self.text = self.label

        try:
            subprocess.Popen([self.command, *self.args, image])
        except subprocess.SubprocessError as err:
            logger.exception("Subprocess error: %s ", str(err))
        self.draw()

    def update(self, text):
        """Update the wallpaper"""
        if not self.update_interval:
            return
        self.set_wallpaper()

    def button_press(self, x, y, button):
        """
        Handle the button press
        """
        # type: (int, int, int) -> None
        if button == 1 and (self.cycle or self.random):
            self.set_wallpaper()
