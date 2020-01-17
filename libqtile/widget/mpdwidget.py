# -*- coding: utf-8 -*-
# Copyright (c) 2010 matt
# Copyright (c) 2010 Dieter Plaetinck
# Copyright (c) 2010, 2012 roger
# Copyright (c) 2011-2012 Florian Mounier
# Copyright (c) 2011 Mounier Florian
# Copyright (c) 2011 Timo Schmiade
# Copyright (c) 2012 Mikkel Oscar Lyderik
# Copyright (c) 2012, 2014 Tycho Andersen
# Copyright (c) 2012 Craig Barnes
# Copyright (c) 2013 Tao Sauvage
# Copyright (c) 2013 Tom Hunt
# Copyright (c) 2014 Justin Bronder
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

from . import base
from .. import utils, pangocffi
from libqtile.log_utils import logger

from socket import error as socket_error
try:
    from musicpd import MPDClient, ConnectionError, CommandError, ProtocolError
except ImportError:
    from mpd import MPDClient, ConnectionError, CommandError, ProtocolError

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


class Mpd(base.ThreadPoolText):
    """A widget for Music Player Daemon (MPD)

    This widget works with python-mpd, python-mpd2 and python-musicpd.

    Parameters
    ==========
    status_format :
        Format string to display status.

        Full list of values see in ``status`` and ``currentsong`` commands

        https://musicpd.org/doc/protocol/command_reference.html#command_status
        https://musicpd.org/doc/protocol/tags.html

        Default::

        {play_status} {artist}/{title} [{repeat}{random}{single}{consume}{updating_db}]

        ``play_status`` is string from ``play_states`` dict

        Note that ``time`` property of song renamed to ``fulltime`` to prevent
        conflicts with status information during formating.

    status_format_stopped :
        Format string to display status when playback is stopped, set as above.

    prepare_status :
        dict of functions to replace values in status or currentsong repies with custom
        values.

        ``f(status, key, space_element) => str``
    """

    orientations = base.ORIENTATION_HORIZONTAL
    defaults = [
        ('update_interval', 1, 'Update time in seconds'),
        ('host', 'localhost', 'Host of mpd server'),
        ('port', 6600, 'Port of mpd server'),
        ('password', None, 'Password for auth on mpd server'),
        ('keys', keys, 'Shortcut keys'),
        ('play_states', play_states, 'Play state mapping'),
        ('command', None, 'Executable command by "command" shortcut'),
        ('timeout', 30, 'MPDClient timeout'),
        ('idletimeout', 5, 'MPDClient idle command timeout'),
        ('no_connection', 'No connection', 'Text when mpd is disconnected'),
        ('space', '-', 'Space keeper'),
        ("do_color_progress", False, "Whether to indicate progress in song by "
                                     "altering message color"),
        ("foreground_progress", "ffffff", "Foreground progress colour"),
        ("reconnect", True, "Attempt to reconnect if initial connection failed"),
    ]

    def __init__(self,
        status_format=default_format,
        status_format_stopped=default_format,
        prepare_status=prepare_status,
        **config
    ):
        super().__init__(None, **config)
        self.add_defaults(Mpd.defaults)
        self.status_format = str(status_format)
        self.status_format_stopped = str(status_format_stopped)
        self.prepare_status = prepare_status
        self.client = MPDClient()
        self.client.timeout = self.timeout
        self.client.port = self.port
        self.client.host = self.host

    @property
    def connected(self):
        try:
            self.client.ping()
        except(socket_error, ConnectionError, CommandError):
            try:
                self.client.connect(self.host, self.port)
            except(socket_error, ConnectionError):
                logger.warning('Failed to connect to mpd.')
                if not self.reconnect:
                    self.__dict__['connected'] = False
                return False

            if self.password:
                try:
                    self.client.password(self.password)
                except CommandError:
                    logger.warning('Failed to authenticate to mpd. Disconnecting')
                    try:
                        self.client.disconnect()
                    except ConnectionError:
                        pass
                    return False

        except ProtocolError:
            self.client.disconnect()
            return self.connected

        return True

    def poll(self):
        if self.connected:
            return self.update_status()
        else:
            return self.no_connection

    def button_press(self, x, y, button):
        if self.connected:
            try:
                self.handle_button_press(x, y, button)
            except (CommandError, BrokenPipeError) as e:
                logger.warning(f'mpd error: {e}')
                logger.warning(f'mpd error: Trying again.')
                if self.connected:
                    try:
                        self.handle_button_press(x, y, button)
                    except (CommandError, BrokenPipeError) as e:
                        logger.warning(f'mpd error: {e}')

            self.update(self.update_status())
        else:
            self.update(self.no_connection)

    def handle_button_press(self, x, y, button):
        if button == self.keys["toggle"]:
            status = self.client.status()
            play_status = status['state']

            if play_status == 'play':
                self.client.pause()
            else:
                self.client.play()

        elif button == self.keys["stop"]:
            self.client.stop()

        elif button == self.keys["previous"]:
            self.client.previous()

        elif button == self.keys["next"]:
            self.client.next()

        elif button == self.keys['command']:
            if self.command:
                self.command(self.client)

    def update_status(self):
        self.client.command_list_ok_begin()
        self.client.status()
        self.client.currentsong()
        status, current_song = self.client.command_list_end()

        return self.formatter(status, current_song)

    def formatter(self, status, currentsong):
        play_status = self.play_states[status['state']]

        if currentsong:
            # Dirty hack to prevent keys conflict
            currentsong['fulltime'] = currentsong.get('time', '0')
            del currentsong['time']

            status.update(currentsong)
        self.prepare_formatting(status)

        if status['state'] == 'stop':
            fmt = self.status_format_stopped
        else:
            fmt = self.status_format

        try:
            text = fmt.format(play_status=play_status, **status)
        except KeyError as e:
            logger.exception(f"mpd client did not return status: {e.args[0]}")
            return "ERROR"

        if self.do_color_progress and status['state'] != 'stop':
            try:
                elapsed, total = status['time'].split(':')
                percent = float(elapsed) / float(total)
                progress = int(percent * len(text))
                text = '<span color="{0}">{1}</span>{2}'.format(
                    utils.hex(self.foreground_progress),
                    pangocffi.markup_escape_text(text[:progress]),
                    pangocffi.markup_escape_text(text[progress:]),
                )
            except (ZeroDivisionError, ValueError):
                pass

        return text

    def prepare_formatting(self, status):
        for key in self.prepare_status:
            self.prepare_status[key](status, key, self.space)

    def finalize(self):
        super().finalize()

        try:
            self.client.close()
            self.client.disconnect()
        except ConnectionError:
            pass
