import os
from functools import partial

from libqtile.widget.generic_poll_text import GenPollCommand


class Moc(GenPollCommand):
    """A simple MOC widget.

    Show the artist and album of now listening song and allow basic mouse
    control from the bar:

    - toggle pause (or play if stopped) on left click;
    - skip forward in playlist on scroll up;
    - skip backward in playlist on scroll down.

    MOC (http://moc.daper.net) should be installed.
    """

    defaults = [
        ("play_color", "00ff00", "Text colour when playing."),
        ("noplay_color", "cecece", "Text colour when not playing."),
        ("update_interval", 0.5, "Update Time in seconds."),
    ]

    def __init__(self, **config):
        config["cmd"] = ["mocp", "-i"]
        GenPollCommand.__init__(self, **config)
        self.add_defaults(Moc.defaults)
        self.status = ""
        self.local = None

        self.add_callbacks(
            {
                "Button1": self.play,
                "Button4": partial(self.call_process, ["mocp", "-f"]),
                "Button5": partial(self.call_process, ["mocp", "-r"]),
            }
        )

    def get_info(self, output):
        """Return a dictionary with info about the current MOC status."""
        if output.startswith("State"):
            output = output.splitlines()
            info = {"State": "", "File": "", "SongTitle": "", "Artist": "", "Album": ""}

            for line in output:
                for data in info:
                    if data in line:
                        info[data] = line[len(data) + 2 :].strip()
                        break
            return info

    def parse(self, output):
        """Return a string with the now playing info (Artist - Song Title)."""
        info = self.get_info(output)
        now_playing = ""
        if info:
            status = info["State"]
            if self.status != status:
                self.status = status
                if self.status == "PLAY":
                    self.layout.colour = self.play_color
                else:
                    self.layout.colour = self.noplay_color
            title = info["SongTitle"]
            artist = info["Artist"]
            if title and artist:
                now_playing = f"♫ {artist} - {title}"
            elif title:
                now_playing = f"♫ {title}"
            else:
                basename = os.path.basename(info["File"])
                filename = os.path.splitext(basename)[0]
                now_playing = f"♫ {filename}"

            if self.status == "STOP":
                now_playing = "♫"

        return now_playing

    def play(self):
        """Play music if stopped, else toggle pause."""
        if self.status in ("PLAY", "PAUSE"):
            self.call_process(["mocp", "-G"])
        elif self.status == "STOP":
            self.call_process(["mocp", "-p"])
