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

import datetime
import math
import subprocess
from functools import partial

from libqtile import pangocffi
from libqtile.widget.generic_poll_text import GenPollCommand


def format_time(time_seconds_string):
    """Format time in seconds as [h:]mm:ss."""
    return str(datetime.timedelta(seconds=float(time_seconds_string))).lstrip("0").lstrip(":")


class Cmus(GenPollCommand):
    """A simple Cmus widget.

    Show the metadata of now listening song and allow basic mouse
    control from the bar:

        - toggle pause (or play if stopped) on left click;
        - skip forward in playlist on scroll up;
        - skip backward in playlist on scroll down.

    The following fields (extracted from ``cmus-remote -C status``) are available in the `format`
    string:

    - ``status``: cmus playback status, one of "playing", "paused" or "stopped".
    - ``file``
    - ``position``: Current position in [h:]mm:ss.
    - ``position_percent``: Current position in percent.
    - ``remaining``: Remaining time in [h:]mm:ss.
    - ``remaining_percent``: Remaining time in percent.
    - ``duration``: Total length in [h:]mm:ss.
    - ``artist``
    - ``album``
    - ``albumartist``
    - ``composer``
    - ``comment``
    - ``date``
    - ``discnumber``
    - ``genre``
    - ``title``: Title or filename if no title is available.
    - ``tracknumber``
    - ``stream``
    - ``status_text``: Text indicating the playback status, corresponds to one of `playing_text`,
      `paused_text` or `stopped_text`.

    Cmus (https://cmus.github.io) should be installed.
    """

    defaults = [
        ("format", "{status_text}{artist} - {title}", "Format of playback info."),
        ("stream_format", "{status_text}{stream}", "Format of playback info for streams."),
        (
            "no_artist_format",
            "{status_text}{title}",
            "Format of playback info if no artist available.",
        ),
        ("playing_text", "♫ ", "Text to display when playing, if chosen."),
        ("playing_color", "00ff00", "Text colour when playing."),
        ("paused_text", "♫ ", "Text to display when paused, if chosen."),
        ("paused_color", "cecece", "Text color when paused."),
        ("stopped_text", "♫ ", "Text to display when stopped, if chosen."),
        ("stopped_color", "cecece", "Text color when stopped."),
        ("update_interval", 0.5, "Update Time in seconds."),
        (
            "play_icon",
            "♫ ",
            "DEPRECATED Text to display when playing, paused, and stopped, if chosen.",
        ),
        ("play_color", "", "DEPRECATED Text colour when playing."),
        ("noplay_color", "", "DEPRECATED Text colour when paused or stopped."),
    ]

    def __init__(self, **config):
        config["cmd"] = ["cmus-remote", "-C", "status"]
        GenPollCommand.__init__(self, **config)
        self.add_defaults(Cmus.defaults)
        self.status = ""
        self.local = None

        self.add_callbacks(
            {
                "Button1": self.play,
                "Button4": partial(subprocess.Popen, ["cmus-remote", "-n"]),
                "Button5": partial(subprocess.Popen, ["cmus-remote", "-r"]),
            }
        )

    def _configure(self, qtile, parent_bar):
        GenPollCommand._configure(self, qtile, parent_bar)
        # Backwards compatibility
        if self.play_color:
            self.playing_color = self.play_color
            self.paused_color = self.play_color
        if self.noplay_color:
            self.stopped_color = self.noplay_color

    def get_info(self, output):
        """Return a dictionary with info about the current cmus status."""
        if output.startswith("status"):
            output = output.splitlines()
            info = {
                "status": "",
                "file": "",
                "position": "",
                "position_percent": "",
                "remaining": "",
                "remaining_percent": "",
                "duration": "",
                "artist": "",
                "album": "",
                "albumartist": "",
                "composer": "",
                "comment": "",
                "date": "",
                "discnumber": "",
                "genre": "",
                "title": "",
                "tracknumber": "",
                "stream": "",
                "status_text": "",
                "play_icon": self.play_icon,
            }

            for line in output:
                if line.startswith("set"):
                    break
                for data in info:
                    match = data + " "
                    if match in line:
                        index = line.index(data)
                        if index < 5:
                            info[data] = line[len(data) + index :].strip()
                            break

            # Set status text
            status = info["status"]
            info["status_text"] = getattr(self, f"{status}_text", self.stopped_text)

            # Format and process duration and position
            if info["position"] != "" and info["duration"] != "" and int(info["duration"]) > 0:
                info["position_percent"] = (
                    str(math.floor(int(info["position"]) / int(info["duration"]) * 100)) + "%"
                )
                info["remaining_percent"] = (
                    str(
                        math.ceil(
                            (int(info["duration"]) - int(info["position"]))
                            / int(info["duration"])
                            * 100
                        )
                    )
                    + "%"
                )
                info["remaining"] = format_time(int(info["duration"]) - int(info["position"]))
                info["position"] = format_time(info["position"])
                info["duration"] = format_time(info["duration"])
            else:
                info["duration"] = ""
                info["position"] = ""

            return info

    def parse(self, output):
        """Return a string with the now playing info."""
        info = self.get_info(output)
        now_playing = ""
        if info:
            display_format = self.format
            status = info["status"]
            if self.status != status:
                self.status = status
                if self.status == "playing":
                    self.layout.colour = self.playing_color
                elif self.status == "paused":
                    self.layout.colour = self.paused_color
                else:
                    self.layout.colour = self.stopped_color
            self.local = info["file"].startswith("/")
            if self.local:
                if not info["title"]:
                    info["title"] = info["file"].split("/")[-1]
                if not info["artist"]:
                    display_format = self.no_artist_format
            elif info["stream"]:
                display_format = self.stream_format
            # Handle case if cmus was started and no file is selected yet
            elif not info["file"]:
                display_format = ""
            now_playing = display_format.format(**info)
            if now_playing.strip() == info["status_text"].strip():
                now_playing = ""

        return pangocffi.markup_escape_text(now_playing)

    def play(self):
        """Play music if stopped, else toggle pause."""
        if self.status in ("playing", "paused"):
            subprocess.Popen(["cmus-remote", "-u"])
        elif self.status == "stopped":
            subprocess.Popen(["cmus-remote", "-p"])
