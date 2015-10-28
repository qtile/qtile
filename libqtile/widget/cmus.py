# -*- coding: utf-8 -*-
# Copyright (C) 2015, Juan Riquelme González
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

import subprocess


class Cmus(base.ThreadPollText):

    """A simple Cmus widget.

    Show the artist and album of now listening song and allow basic mouse
    control from the bar:
        - toggle pause (or play if stopped) on left click;
        - skip forward in playlist on scroll up;
        - skip backward in playlist on scroll down.

    Cmus (https://cmus.github.io) should be installed.
    """
    orientations = base.ORIENTATION_HORIZONTAL
    defaults = [
        ('play_color', '00ff00', 'Text colour when playing.'),
        ('noplay_color', 'cecece', 'Text colour when not playing.'),
        ('max_chars', 0, 'Maximum number of characters to display in widget.')
    ]

    def __init__(self, **config):
        base.ThreadPollText.__init__(self, "", **config)
        self.add_defaults(Cmus.defaults)
        self.status = ""
        self.local = None

    def get_info(self):
        """Return a dictionary with info about the current cmus status."""
        try:
            output = self.call_process(['cmus-remote', '-Q'])
        except subprocess.CalledProcessError as err:
            output = err.output.decode()
        if output.startswith("status"):
            output = output.splitlines()
            info = {'status': "",
                    'file': "",
                    'artist': "",
                    'album': "",
                    'title': "",
                    'stream': ""}

            for line in output:
                for data in info:
                    if data in line:
                        index = line.index(data)
                        if index < 5:
                            info[data] = line[len(data) + index:].strip()
                            break
                    elif line.startswith("set"):
                        return info
            return info

    def now_playing(self):
        """Return a string with the now playing info (Artist - Song Title)."""
        info = self.get_info()
        now_playing = ""
        if info:
            status = info['status']
            if self.status != status:
                self.status = status
                if self.status == "playing":
                    self.layout.colour = self.play_color
                else:
                    self.layout.colour = self.noplay_color
            self.local = info['file'].startswith("/")
            title = info['title']
            if self.local:
                artist = info['artist']
                now_playing = "{0} - {1}".format(artist, title)
            else:
                if info['stream']:
                    now_playing = info['stream']
                else:
                    now_playing = title
            if now_playing:
                now_playing = "♫ {0}".format(now_playing)
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
            if self.status in ('playing', 'paused'):
                subprocess.Popen(['cmus-remote', '-u'])
            elif self.status == 'stopped':
                subprocess.Popen(['cmus-remote', '-p'])
        elif button == 4:
            subprocess.Popen(['cmus-remote', '-n'])
        elif button == 5:
            subprocess.Popen(['cmus-remote', '-r'])
