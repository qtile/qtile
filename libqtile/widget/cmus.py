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

import subprocess
from functools import partial

from libqtile import pangocffi
from libqtile.widget import base


class Cmus(base.ThreadPoolText):
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
        ('update_interval', 0.5, 'Update Time in seconds.')
    ]

    def __init__(self, **config):
        base.ThreadPoolText.__init__(self, "", **config)
        self.add_defaults(Cmus.defaults)
        self.status = ""
        self.local = None

        self.add_callbacks({
            'Button1': self.play,
            'Button4': partial(subprocess.Popen, ['cmus-remote', '-n']),
            'Button5': partial(subprocess.Popen, ['cmus-remote', '-r']),
        })

    def get_info(self):
        """Return a dictionary with info about the current cmus status."""
        try:
            output = self.call_process(['cmus-remote', '-C', 'status'])
        except subprocess.CalledProcessError as err:
            output = err.output
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
        return pangocffi.markup_escape_text(now_playing)

    def play(self):
        """Play music if stopped, else toggle pause."""
        if self.status in ('playing', 'paused'):
            subprocess.Popen(['cmus-remote', '-u'])
        elif self.status == 'stopped':
            subprocess.Popen(['cmus-remote', '-p'])

    def poll(self):
        """Poll content for the text box."""
        return self.now_playing()
