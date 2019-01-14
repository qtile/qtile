from . import base
from libqtile.log_utils import logger

from socket import error as socket_error
from mpd import MPDClient, ConnectionError, CommandError

# Shortcuts
# TODO: Volume inc/dec support
keys = {
    # Left mouse button
    "toggle": 1,
    # Right mouse button
    "stop": 3,
    # Scroll up
    "previous": 4,
    # Scroll down
    "next": 5,
    # User defined command
    "command": None
}

# To display mpd state
play_states = {
    'play': '\u25b6',
    'pause': '\u23F8',
    'stop': '\u25a0',
}


def option(char):
    def _convert(elements, key, space):
        if key in elements and elements[key] != '0':
            elements[key] = char
        else:
            elements[key] = space
    return _convert


prepare_status = {
    'repeat': option('r'),
    'random': option('z'),
    'single': option('1'),
    'consume': option('c'),
    'updating_db': option('U')
}

default_format = '{play_status} {artist}/{title} ' +\
                 '[{repeat}{random}{single}{consume}{updating_db}]'


class Mpd2(base.ThreadPoolText):
    """A widget for Music Player Daemon (MPD) based on python-mpd2

    This widget exists since python-mpd library is no more supported.

    Parameters
    ==========
    status_format :
        format string to display status

        Full list of values see in ``status`` and ``currentsong`` commands

        https://musicpd.org/doc/protocol/command_reference.html#command_status
        https://musicpd.org/doc/protocol/tags.html

        Default::

        {play_status} {artist}/{title} [{repeat}{random}{single}{consume}{updating_db}]

        ``play_status`` is string from ``play_states`` dict

        Note that ``time`` property of song renamed to ``fulltime`` to prevent
        conflicts with status information during formating.

    prepare_status :
        dict of functions for replace values in status with custom

        ``f(status, key, space_element) => str``
    """

    orientations = base.ORIENTATION_HORIZONTAL
    defaults = [
        ('update_interval', 1, 'Interval of update widget'),
        ('host', 'localhost', 'Host of mpd server'),
        ('port', 6600, 'Port of mpd server'),
        ('password', None, 'Password for auth on mpd server'),
        ('keys', keys, 'Shortcut keys'),
        ('play_states', play_states, 'Play state mapping'),
        ('command', None, 'Executable command by "command" shortcut'),
        ('timeout', 30, 'MPDClient timeout'),
        ('idletimeout', 5, 'MPDClient idle command timeout'),
        ('no_connection', 'No connection', 'Text when mpd is disconnected'),
        ('space', '-', 'Space keeper')
    ]

    def __init__(self, status_format=default_format,
                 prepare_status=prepare_status, **config):
        super(Mpd2, self).__init__(None, **config)
        self.add_defaults(Mpd2.defaults)
        self.status_format = status_format
        self.prepare_status = prepare_status
        self.connected = False
        self.client = MPDClient()
        self.client.timeout = self.timeout
        self.client.idletimeout = self.idletimeout
        self.try_reconnect()

    def try_reconnect(self):
        if not self.connected:
            try:
                self.client.ping()
            except(socket_error, ConnectionError):
                try:
                    self.client.connect(self.host, self.port)
                    if self.password:
                        self.client.password(self.password)
                    self.connected = True
                except(socket_error, ConnectionError, CommandError):
                    self.connected = False

    def poll(self):
        self.try_reconnect()

        if self.connected:
            return self.update_status()
        else:
            return self.no_connection

    def update_status(self):
        self.client.command_list_ok_begin()
        self.client.status()
        self.client.currentsong()
        status, current_song = self.client.command_list_end()

        return self.formatter(status, current_song)

    # TODO: Resolve timeouts on the method call
    def button_press(self, x, y, button):
        self.try_reconnect()
        if self.connected:
            self[button]

    def __getitem__(self, key):
        if key == self.keys["toggle"]:
            status = self.client.status()
            play_status = status['state']

            if play_status == 'play':
                self.client.pause()
            else:
                self.client.play()

        if key == self.keys["stop"]:
            self.client.stop()

        if key == self.keys["previous"]:
            self.client.previous()

        if key == self.keys["next"]:
            self.client.next()

        if key == self.keys['command']:
            if self.command:
                self.command(self.client)

        self.update(self.update_status)

    def formatter(self, status, currentsong):
        play_status = self.play_states[status['state']]

        # Dirty hack to prevent keys conflict
        currentsong['fulltime'] = currentsong['time']
        del currentsong['time']

        self.prepare_formatting(status, currentsong)
        status.update(currentsong)

        fmt = self.status_format
        if not isinstance(fmt, str):
            fmt = str(fmt)

        try:
            formatted = fmt.format(play_status=play_status, **status)
            return formatted
        except KeyError as e:
            logger.exception("mpd client did not return status: {}".format(e.args[0]))
            return "ERROR"

    def prepare_formatting(self, status, currentsong):
        for key in self.prepare_status:
            self.prepare_status[key](status, key, self.space)

    def finalize(self):
        super(Mpd2, self).finalize()

        try:
            self.client.close()
            self.client.disconnect()
        except ConnectionError:
            pass
