# -*- coding: utf-8 -*-
# Copyright (C) 2015, zordsdavini
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

from . import base

import os
import subprocess


class Moc(base.ThreadPoolText):

    """A simple MOC widget.

    Show the artist and album of now listening song and allow basic mouse
    control from the bar:
        - toggle pause (or play if stopped) on left click;
        - skip forward in playlist on scroll up;
        - skip backward in playlist on scroll down.

    MOC (http://moc.daper.net) should be installed.
    """
    orientations = base.ORIENTATION_HORIZONTAL
    defaults = [
        ('play_color', '00ff00', 'Text colour when playing.'),
        ('noplay_color', 'cecece', 'Text colour when not playing.'),
        ('max_chars', 0, 'Maximum number of characters to display in widget.'),
        ('update_interval', 0.5, 'Update Time in seconds.'),
    ]

    def __init__(self, **config):
        base.ThreadPoolText.__init__(self, "", **config)
        self.add_defaults(Moc.defaults)
        self.status = ""
        self.local = None

    def get_info(self):
        """Return a dictionary with info about the current MOC status."""
        try:
            output = self.call_process(['mocp', '-i'])
        except subprocess.CalledProcessError as err:
            output = err.output.decode()
        if output.startswith("State"):
            output = output.splitlines()
            info = {'State': "",
                    'File': "",
                    'SongTitle': "",
                    'Artist': "",
                    'Album': ""}

            for line in output:
                for data in info:
                    if data in line:
                        info[data] = line[len(data) + 2:].strip()
                        break
            return info

    def now_playing(self):
        """Return a string with the now playing info (Artist - Song Title)."""
        info = self.get_info()
        now_playing = ""
        if info:
            status = info['State']
            if self.status != status:
                self.status = status
                if self.status == "PLAY":
                    self.layout.colour = self.play_color
                else:
                    self.layout.colour = self.noplay_color
            title = info['SongTitle']
            artist = info['Artist']
            if title and artist:
                now_playing = "♫ {0} - {1}".format(artist, title)
            else:
                basename = os.path.basename(info['File'])
                filename = os.path.splitext(basename)[0]
                now_playing = "♫ {0}".format(filename)

            if self.status == "STOP":
                now_playing = "♫"

        return now_playing

    def update(self, text):
        """Update the text box."""
        old_width = self.layout.width
        if not self.status:
            return
        if len(text) > self.max_chars > 0:
            text = text[:self.max_chars] + "…"
        self.text = text

        if self.layout.width == old_width:
            self.draw()
        else:
            self.bar.draw()

    def poll(self):
        """Poll content for the text box."""
        return self.now_playing()

    def button_press(self, x, y, button):
        """What to do when press a mouse button over the cmus widget.

        Will:
            - toggle pause (or play if stopped) on left click;
            - skip forward in playlist on scroll up;
            - skip backward in playlist on scroll down.
        """
        if button == 1:
            if self.status in ('PLAY', 'PAUSE'):
                subprocess.Popen(['mocp', '-G'])
            elif self.status == 'STOP':
                subprocess.Popen(['mocp', '-p'])
        elif button == 4:
            subprocess.Popen(['mocp', '-f'])
        elif button == 5:
            subprocess.Popen(['mocp', '-r'])
