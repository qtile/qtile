# -*- coding: utf-8 -*-
# depends on python-mpd


# TODO: check if UI hangs in case of network issues and such
# TODO: python-mpd supports idle proto, can widgets be push instead of pull?
# TODO: a teardown hook so I can client.disconnect() ?
# TODO: some kind of templating to make shown info configurable
# TODO: best practice to handle failures? just write to stderr?

from .. import bar, utils
from mpd import MPDClient, CommandError
import atexit
import base
import re


class Mpd(base._TextBox):
    """
        An mpd widget
    """
    defaults = [
        ("foreground_progress", "ffffff", "Foreground progress colour"),
        (
            "reconnect",
            False,
            "Choose if the widget should try to keep reconnect."
        )
    ]

    def __init__(self, width=bar.CALCULATED, host='localhost', port=6600,
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
        self.host = host
        self.port = port
        self.password = password
        self.fmt_playing, self.fmt_stopped = fmt_playing, fmt_stopped
        self.msg_nc = msg_nc
        self.do_color_progress = do_color_progress
        self.inc = 2
        base._TextBox.__init__(self, " ", width, **config)
        self.add_defaults(Mpd.defaults)
        self.client = MPDClient()
        self.connected = False
        self.connect()
        self.timeout_add(1, self.update)

    def connect(self, ifneeded=False):
        if self.connected:
            if not ifneeded:
                self.log.warning(
                    'Already connected. '
                    'No need to connect again. '
                    'Maybe you want to disconnect first.'
                )
            return True
        CON_ID = {'host': self.host, 'port': self.port}
        if not self.mpdConnect(CON_ID):
            self.log.error('Cannot connect to MPD server.')
        if self.password:
            if not self.mpdAuth(self.password):
                self.log.warning('Authentication failed.  Disconnecting')
                try:
                    self.client.disconnect()
                except Exception:
                    self.log.exception('Error disconnecting mpd')
        return self.connected

    def mpdConnect(self, con_id):
        """
            Simple wrapper to connect MPD.
        """
        try:
            self.client.connect(**con_id)
        except Exception:
            self.log.exception('Error connecting mpd')
            return False
        self.connected = True
        return True

    def mpdDisconnect(self):
        """
            Simple wrapper to disconnect MPD.
        """
        try:
            self.client.disconnect()
        except Exception:
            self.log.exception('Error disconnecting mpd')
            return False
        self.connected = False
        return True

    def mpdAuth(self, secret):
        """
            Authenticate
        """
        try:
            self.client.password(secret)
        except CommandError:
            return False
        return True

    def _configure(self, qtile, bar):
        base._TextBox._configure(self, qtile, bar)
        self.layout = self.drawer.textlayout(
            self.text,
            self.foreground,
            self.font,
            self.fontsize,
            self.fontshadow,
            markup=True
        )
        atexit.register(self.mpdDisconnect)

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
        return str(int(self.status['song'])+1)

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

    def update(self):
        if not self.configured:
            return True
        if self.connect(True):
            try:
                self.status = self.client.status()
                self.song = self.client.currentsong()
                if self.status['state'] != 'stop':
                    playing = self.do_format(self.fmt_playing)

                    if self.do_color_progress and \
                            self.status and \
                            self.status.get('time', None):
                        elapsed, total = self.status['time'].split(':')
                        percent = float(elapsed) / float(total)
                        progress = int(percent * len(playing))
                        playing = '<span color="%s">%s</span>%s' % (
                            utils.hex(self.foreground_progress),
                            utils.escape(playing[:progress]),
                            utils.escape(playing[progress:])
                        )
                    else:
                        playing = utils.escape(playing)
                else:
                    playing = self.do_format(self.fmt_stopped)

            except Exception:
                self.log.exception('Mpd error on update')
                playing = self.msg_nc
                self.mpdDisconnect()
        else:
            if self.reconnect:
                playing = self.msg_nc
            else:
                return False

        if self.text != playing:
            self.text = playing
            self.bar.draw()

        return True

    def button_press(self, x, y, button):
        if not self.connect(True):
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
