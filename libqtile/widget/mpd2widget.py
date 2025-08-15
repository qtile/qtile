"""
A widget for Music Player Daemon (MPD) based on python-mpd2.

This widget exists since python-mpd library is no longer supported.
"""

from collections import defaultdict
from html import escape

from mpd import CommandError, ConnectionError, MPDClient

from libqtile import utils
from libqtile.log_utils import logger
from libqtile.widget import base

# Mouse Interaction
# TODO: Volume inc/dec support
keys = {
    # Left mouse button
    1: "toggle",
    # Right mouse button
    3: "stop",
    # Scroll up
    4: "previous",
    # Scroll down
    5: "next",
}

# To display mpd state
play_states = {"play": "\u25b6", "pause": "\u23f8", "stop": "\u25a0"}


def option(char):
    """
    old status mapping method.

    Deprecated.
    """

    def _convert(elements, key, space):
        if key in elements and elements[key] != "0":
            elements[key] = char
        else:
            elements[key] = space

    return _convert


# Changes to formatter will still use this dicitionary as a fallback
prepare_status = {
    "repeat": option("r"),
    "random": option("z"),
    "single": option("1"),
    "consume": option("c"),
    "updating_db": option("U"),
}

# dictionary for new formatting method.  This is now default.
status_dict = {"repeat": "r", "random": "z", "single": "1", "consume": "c", "updating_db": "U"}

default_idle_message = "MPD IDLE"

default_idle_format = (
    "{play_status} {idle_message}" + "[{repeat}{random}{single}{consume}{updating_db}]"
)

default_format = (
    "{play_status} {artist}/{title} " + "[{repeat}{random}{single}{consume}{updating_db}]"
)

default_undefined_status_value = "Undefined"


def default_cmd():
    return None


format_fns = {
    "all": escape,
}


class Mpd2(base.BackgroundPoll):
    r"""Mpd2 Object.

    Parameters
    ==========
    status_format:
        format string to display status

        For a full list of values, see:
            MPDClient.status() and MPDClient.currentsong()

        https://musicpd.org/doc/protocol/command_reference.html#command_status
        https://musicpd.org/doc/protocol/tags.html

        Default::

            '{play_status} {artist}/{title} \
                [{repeat}{random}{single}{consume}{updating_db}]'

            ``play_status`` is a string from ``play_states`` dict

            Note that the ``time`` property of the song renamed to ``fulltime``
            to prevent conflicts with status information during formating.

    idle_format:
        format string to display status when no song is in queue.

        Default::

            '{play_status} {idle_message} \
                [{repeat}{random}{single}{consume}{updating_db}]'

            Note that the ``artist`` key fallbacks to similar keys in specific order.
            (``artist`` -> ``albumartist`` -> ``performer`` ->
             -> ``composer`` -> ``conductor`` -> ``ensemble``)

    idle_message:
        text to display instead of song information when MPD is idle.
        (i.e. no song in queue)

        Default:: "MPD IDLE"

    undefined_value:
        text to display when status key is undefined

        Default:: "Undefined"

    prepare_status:
        dict of functions to replace values in status with custom characters.

        ``f(status, key, space_element) => str``

        New functionality allows use of a dictionary of plain strings.

        Default::

            status_dict = {
                'repeat': 'r',
                'random': 'z',
                'single': '1',
                'consume': 'c',
                'updating_db': 'U'
            }

    format_fns:
        A dict of functions to format the various elements.

        'Tag': f(str) => str

        Default:: { 'all': lambda s: cgi.escape(s) }

        N.B. if 'all' is present, it is processed on every element of song_info
            before any other formatting is done.

    mouse_buttons:
        A dict of mouse button numbers to actions

    Widget requirements: python-mpd2_.

    .. _python-mpd2: https://pypi.org/project/python-mpd2/
    """

    defaults = [
        ("update_interval", 1, "Interval of update widget"),
        ("host", "localhost", "Host of mpd server"),
        ("port", 6600, "Port of mpd server"),
        ("password", None, "Password for auth on mpd server"),
        ("mouse_buttons", keys, "b_num -> action."),
        ("play_states", play_states, "Play state mapping"),
        ("format_fns", format_fns, "Dictionary of format methods"),
        ("command", default_cmd, "command to be executed by mapped mouse button."),
        ("prepare_status", status_dict, "characters to show the status of MPD"),
        ("status_format", default_format, "format for displayed song info."),
        ("idle_format", default_idle_format, "format for status when mpd has no playlist."),
        ("idle_message", default_idle_message, "text to display when mpd is idle."),
        (
            "undefined_value",
            default_undefined_status_value,
            "text to display when status key is undefined.",
        ),
        ("timeout", 30, "MPDClient timeout"),
        ("idletimeout", 5, "MPDClient idle command timeout"),
        ("no_connection", "No connection", "Text when mpd is disconnected"),
        ("color_progress", None, "Text color to indicate track progress."),
        ("space", "-", "Space keeper"),
    ]

    def __init__(self, **config):
        """Constructor."""
        super().__init__("", **config)

        self.add_defaults(Mpd2.defaults)
        if self.color_progress:
            self.color_progress = utils.hex(self.color_progress)

    def _configure(self, qtile, bar):
        super()._configure(qtile, bar)
        self.client = MPDClient()
        self.client.timeout = self.timeout
        self.client.idletimeout = self.idletimeout

    @property
    def connected(self):
        """Attempt connection to mpd server."""
        try:
            self.client.ping()  # pylint: disable=E1101
        except (OSError, ConnectionError):
            try:
                self.client.connect(self.host, self.port)
                if self.password:
                    self.client.password(self.password)  # pylint: disable=E1101
            except (OSError, ConnectionError, CommandError):
                return False
        return True

    def poll(self):
        """
        Called by qtile manager.

        poll the mpd server and update widget.
        """
        if self.connected:
            return self.update_status()
        else:
            return self.no_connection

    def update_status(self):
        """get updated info from mpd server and call format."""
        self.client.command_list_ok_begin()
        self.client.status()  # pylint: disable=E1101
        self.client.currentsong()  # pylint: disable=E1101
        status, current_song = self.client.command_list_end()

        return self.formatter(status, current_song)

    def button_press(self, x, y, button):
        """handle click event on widget."""
        base.BackgroundPoll.button_press(self, x, y, button)
        m_name = self.mouse_buttons[button]

        if self.connected:
            if hasattr(self, m_name):
                self.__try_call(m_name)
            elif hasattr(self.client, m_name):
                self.__try_call(m_name, self.client)

    def __try_call(self, attr_name, obj=None):
        err1 = "Class {Class} has no attribute {attr}."
        err2 = 'attribute "{Class}.{attr}" is not callable.'
        context = obj or self
        try:
            getattr(context, attr_name)()
        except (AttributeError, TypeError) as e:
            if isinstance(e, AttributeError):
                err = err1.format(Class=type(context).__name__, attr=attr_name)
            else:
                err = err2.format(Class=type(context).__name__, attr=attr_name)
            logger.exception("%s %s", err, e.args[0])

    def toggle(self):
        """toggle play/pause."""
        status = self.client.status()  # pylint: disable=E1101
        play_status = status["state"]

        if play_status == "play":
            self.client.pause()  # pylint: disable=E1101
        else:
            self.client.play()  # pylint: disable=E1101

    def formatter(self, status, current_song):
        """format song info."""
        song_info = defaultdict(lambda: self.undefined_value)
        song_info["play_status"] = self.play_states[status["state"]]

        if status["state"] == "stop" and current_song == {}:
            song_info["idle_message"] = self.idle_message
            fmt = self.idle_format
        else:
            fmt = self.status_format

        for k in current_song:
            song_info[k] = current_song[k]
        song_info["fulltime"] = song_info["time"]
        del song_info["time"]

        song_info.update(status)
        if song_info["updating_db"] == self.undefined_value:
            song_info["updating_db"] = "0"
        if not callable(self.prepare_status["repeat"]):
            for k in self.prepare_status:
                if k in status and status[k] != "0":
                    # Much more direct.
                    song_info[k] = self.prepare_status[k]
                else:
                    song_info[k] = self.space
        else:
            self.prepare_formatting(song_info)

        # 'remaining' isn't actually in the information provided by mpd
        # so we construct it from 'fulltime' and 'elapsed'.
        # 'elapsed' is always less than or equal to 'fulltime', if it exists.
        # Remaining should default to '00:00' if either or both are missing.
        # These values are also used for coloring text by progress, if wanted.
        if "remaining" in self.status_format or self.color_progress:
            total = (
                float(song_info["fulltime"])
                if song_info["fulltime"] != self.undefined_value
                else 0.0
            )
            elapsed = (
                float(song_info["elapsed"])
                if song_info["elapsed"] != self.undefined_value
                else 0.0
            )
            song_info["remaining"] = f"{float(total - elapsed):.2f}"

        if "song" in self.status_format and song_info["song"] != self.undefined_value:
            song_info["currentsong"] = str(int(song_info["song"]) + 1)

        if "artist" in self.status_format and song_info["artist"] == self.undefined_value:
            artist_keys = ("albumartist", "performer", "composer", "conductor", "ensemble")
            for key in artist_keys:
                if song_info[key] != self.undefined_value:
                    song_info["artist"] = song_info[key]
                    break

        # mpd serializes tags containing commas as lists.
        for key in song_info:
            if isinstance(song_info[key], list):
                song_info[key] = ", ".join(song_info[key])

        # Now we apply the user formatting to selected elements in song_info.
        # if 'all' is defined, it is applied first.
        # the reason for this is that, if the format functions do pango markup.
        # we don't want to do anything that would mess it up, e.g. `escape`ing.
        if "all" in self.format_fns:
            for key in song_info:
                song_info[key] = self.format_fns["all"](song_info[key])
        for fmt_fn in self.format_fns:
            if fmt_fn in song_info and fmt_fn != "all":
                song_info[fmt_fn] = self.format_fns[fmt_fn](song_info[fmt_fn])

        # fmt = self.status_format
        if not isinstance(fmt, str):
            fmt = str(fmt)

        formatted = fmt.format_map(song_info)

        if self.color_progress and status["state"] != "stop":
            try:
                progress = int(len(formatted) * elapsed / total)
                formatted = f'<span color="{self.color_progress}">{formatted[:progress]}</span>{formatted[progress:]}'
            except (ZeroDivisionError, ValueError):
                pass

        return formatted

    def prepare_formatting(self, status):
        """old way of preparing status formatting."""
        for key in self.prepare_status:
            self.prepare_status[key](status, key, self.space)

    def finalize(self):
        """finalize."""
        super().finalize()

        try:
            self.client.close()  # pylint: disable=E1101
            self.client.disconnect()
        except ConnectionError:
            pass
