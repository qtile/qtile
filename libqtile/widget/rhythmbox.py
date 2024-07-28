# Copyright (C) 2015, Juan Riquelme González
# Copyright (C) 2023, Elijah Smith
#
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied
# warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with this program. If not, see
# <http://www.gnu.org/licenses/>.

import subprocess

from functools import partial

from libqtile import pangocffi
from libqtile.widget import base


class Rhythmbox(base.ThreadPoolText):
    """
    A simple Rhythmbox widget that is based on the Cmus widget.

    Show details about the paused or playing song, and allow basic mouse control from the bar:
        - Toggle pause (if playing) or play (if paused) on left click
        - Skip forward in playlist on scroll up
        - Skip backward in playlist on scroll down

    The following options (extracted from ``man rhythmbox-client``) are available for the `format` string:

    - ``%at``: album title
    - ``%aa``: album artist
    - ``%aA``: album artist (lowercase)
    - ``%as``: album artist sortname
    - ``%aS``: album artist sortname (lowercase)
    - ``%ay``: album year
    - ``%ag``: album genre
    - ``%aG``: album genre (lowercase)
    - ``%an``: album disc number
    - ``%aN``: album disc number, zero padded
    - ``%st``: stream title
    - ``%tn``: track number (i.e., 8)
    - ``%tN``: track number, zero padded (i.e., 08)
    - ``%tt``: track title
    - ``%ta``: track artist
    - ``%tA``: track artist (lowercase)
    - ``%ts``: track artist sortname
    - ``%tS``: track artist sortname (lowercase)
    - ``%td``: track duration
    - ``%te``: track elapsed time

    Rhythmbox (https://www.rhythmbox.org/) and Playerctl (https://github.com/altdesktop/playerctl) should be installed.
    """

    defaults = [
        ("format", "%aa - %tt"),
        ("play_color", "00ff00", "Text color when playing."),
        ("no_play_color", "cecece", "Text color when not playing."),
        ("update_interval", 0.5, "Update time in seconds."),
    ]

    def __init__(self, **config):
        base.ThreadPoolText.__init__(self, "", **config)
        self.add_defaults(Rhythmbox.defaults)
        self.status = ""

        self.add_callbacks(
            {
                "Button1": self.play,
                "Button4": partial(subprocess.Popen, ["rhythmbox-client", "--next"]),
                "Button5": partial(subprocess.Popen, ["rhythmbox-client", "--previous"]),
            }
        )

    def play(self):

        if self.status == "Stopped":
            subprocess.Popen(["rhythmbox-client", "--play"])
        elif self.status in ("Paused", "Playing"):
            subprocess.Popen(["rhythmbox-client", "--play-pause"])

    def now_playing(self):
        """Return a string with the details of the now-playing or paused song."""
        now_playing = subprocess.run(
            ['rhythmbox-client', f"--print-playing-format={self.format}"],
            text=True,
            capture_output=True
        ).stdout.strip()

        status = subprocess.run(["playerctl", "--player=rhythmbox", "status"], capture_output=True, text=True).stdout.strip()

        if self.status != status:
            self.status = status

        if self.status == "Playing":
            self.layout.colour = self.play_color
            return f" {pangocffi.markup_escape_text(now_playing)}"
        else:
            self.layout.colour = self.no_play_color

            if self.status == "Paused":
                return f" {pangocffi.markup_escape_text(now_playing)}"
            elif self.status == "Stopped":
                return " No Song Playing"
            else:
                return ""

    def poll(self):
        """Poll content for the text box."""
        return self.now_playing()
