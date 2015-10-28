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

# -*- coding: utf-8 -*-
# depends on python-mpd


# TODO: check if UI hangs in case of network issues and such
# TODO: some kind of templating to make shown info configurable
# TODO: best practice to handle failures? just write to stderr?

from __future__ import division

import re
import time

import mpd

from .. import utils, pangocffi
from . import base

class Mpd(base.ThreadPollText):
    """
        An mpd widget.
    """
    orientations = base.ORIENTATION_HORIZONTAL
    defaults = [
        ("foreground_progress", "ffffff", "Foreground progress colour"),
        ('reconnect', False, 'attempt to reconnect if initial connection failed'),
        ('reconnect_interval', 1, 'Time to delay between connection attempts.')
    ]

    # TODO: have this use our config framework
    def __init__(self, host='localhost', port=6600,
                 password=False, fmt_playing="%a - %t [%v%%]",
                 fmt_stopped="Stopped [%v%%]", msg_nc='Mpd off',
                 do_color_progress=True, **config):
        """
            - host: host to connect to
            - port: port to connect to
            - password: password to use
            - fmt_playing, fmt_stopped: format strings to display when playing/paused and when stopped, respectively
            - msg_nc: which message to show when we're not connected
            - do_color_progress: whether to indicate progress in song by altering message color
            - width: A fixed width, or bar.CALCULATED to calculate the width
            automatically (which is recommended).
        """
        super(Mpd, self).__init__(msg_nc, **config)
        self.host = host
        self.port = port
        self.password = password
        self.fmt_playing, self.fmt_stopped = fmt_playing, fmt_stopped
        self.msg_nc = msg_nc
        self.do_color_progress = do_color_progress
        self.inc = 2
        self.add_defaults(Mpd.defaults)
        self.client = mpd.MPDClient()
        self.connected = False
        self.stop = False

    def finalize(self):
        self.stop = True

        if self.connected:
            try:
                # The volume settings is kind of a dirty trick.  There doesn't
                # seem to be a decent way to set a timeout for the idle
                # command.  Therefore we need to trigger some events such that
                # if poll() is currently waiting on an idle event it will get
                # something so that it can exit.  In practice, I can't tell the
                # difference in volume and hopefully no one else can either.
                self.client.volume(1)
                self.client.volume(-1)
                self.client.disconnect()
            except:
                pass
        base._Widget.finalize(self)

    def connect(self, quiet=False):
        if self.connected:
            return True

        try:
            self.client.connect(host=self.host, port=self.port)
        except Exception:
            if not quiet:
                self.log.exception('Failed to connect to mpd')
            return False

        if self.password:
            try:
                self.client.password(self.password)
            except Exception:
                self.log.warning('Authentication failed.  Disconnecting')
                try:
                    self.client.disconnect()
                except Exception:
                    pass

        self.connected = True
        return True

    def _configure(self, qtile, bar):
        super(Mpd, self)._configure(qtile, bar)
        self.layout = self.drawer.textlayout(
            self.text,
            self.foreground,
            self.font,
            self.fontsize,
            self.fontshadow,
            markup=True
        )

    def to_minutes_seconds(self, stime):
        """Takes an integer time in seconds, transforms it into
        (HH:)?MM:SS. HH portion is only visible if total time is greater
        than an hour.
        """
        if type(stime) != int:
            stime = int(stime)
        mm = stime // 60
        ss = stime % 60
        if mm >= 60:
            hh = mm // 60
            mm = mm % 60
            rv = "{}:{:02}:{:02}".format(hh, mm, ss)
        else:
            rv = "{}:{:02}".format(mm, ss)
        return rv

    def get_artist(self):
        return self.song['artist']

    def get_album(self):
        return self.song['album']

    def get_elapsed(self):
        elapsed = self.status['time'].split(':')[0]
        return self.to_minutes_seconds(elapsed)

    def get_file(self):
        return self.song['file']

    def get_length(self):
        return self.to_minutes_seconds(self.song['time'])

    def get_number(self):
        return str(int(self.status['song']) + 1)

    def get_playlistlength(self):
        return self.status['playlistlength']

    def get_status(self):
        n = self.status['state']
        if n == "play":
            return "->"
        elif n == "pause":
            return "||"
        elif n == "stop":
            return "[]"

    def get_longstatus(self):
        n = self.status['state']
        if n == "play":
            return "Playing"
        elif n == "pause":
            return "Paused"
        elif n == "stop":
            return "Stopped"

    def get_title(self):
        return self.song['title']

    def get_track(self):
        # This occasionally has leading zeros we don't want.
        return str(int(self.song['track'].split('/')[0]))

    def get_volume(self):
        return self.status['volume']

    def get_single(self):
        if self.status['single'] == '1':
            return '1'
        else:
            return '_'

    def get_repeat(self):
        if self.status['repeat'] == '1':
            return 'R'
        else:
            return '_'

    def get_shuffle(self):
        if self.status['random'] == '1':
            return 'S'
        else:
            return '_'

    formats = {
        'a': get_artist, 'A': get_album, 'e': get_elapsed,
        'f': get_file, 'l': get_length, 'n': get_number,
        'p': get_playlistlength, 's': get_status, 'S': get_longstatus,
        't': get_title, 'T': get_track, 'v': get_volume, '1': get_single,
        'r': get_repeat, 'h': get_shuffle, '%': lambda x: '%',
    }

    def match_check(self, m):
        try:
            return self.formats[m.group(1)](self)
        except KeyError:
            return "(nil)"

    def do_format(self, string):
        return re.sub("%(.)", self.match_check, string)

    def _get_status(self):
        playing = self.msg_nc

        try:
            self.status = self.client.status()
            self.song = self.client.currentsong()
            if self.status['state'] != 'stop':
                text = self.do_format(self.fmt_playing)

                if (self.do_color_progress and
                        self.status and
                        self.status.get('time', None)):
                    elapsed, total = self.status['time'].split(':')
                    percent = float(elapsed) / float(total)
                    progress = int(percent * len(text))
                    playing = '<span color="%s">%s</span>%s' % (
                        utils.hex(self.foreground_progress),
                        pangocffi.markup_escape_text(text[:progress]),
                        pangocffi.markup_escape_text(text[progress:])
                    )
                else:
                    playing = pangocffi.markup_escape_text(text)
            else:
                playing = self.do_format(self.fmt_stopped)

        except Exception:
            self.log.exception('Mpd error on update')

        return playing

    def poll(self):
        was_connected = self.connected

        if not self.connected:
            if self.reconnect:
                while not self.stop and not self.connect(quiet=True):
                    time.sleep(self.reconnect_interval)
            else:
                return

        if self.stop:
            return

        if was_connected:
            try:
                self.client.send_idle()
                self.client.fetch_idle()
            except mpd.ConnectionError:
                self.client.disconnect()
                self.connected = False
                return self.msg_nc
            except Exception:
                self.log.exception('Error communicating with mpd')
                self.client.disconnect()
                return

        return self._get_status()

    def button_press(self, x, y, button):
        if not self.connect():
            return False
        try:
            status = self.client.status()
            if button == 3:
                if not status:
                    self.client.play()
                else:
                    self.client.pause()
            elif button == 4:
                self.client.previous()
            elif button == 5:
                self.client.next()
            elif button == 8:
                if status:
                    self.client.setvol(
                        max(int(status['volume']) - self.inc, 0)
                    )
            elif button == 9:
                if status:
                    self.client.setvol(
                        min(int(status['volume']) + self.inc, 100)
                    )
        except Exception:
            self.log.exception('Mpd error on click')
