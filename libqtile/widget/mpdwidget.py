# -*- coding: utf-8 -*-
# depends on python-mpd


# TODO: check if UI hangs in case of network issues and such
# TODO: python-mpd supports idle proto, can widgets be push instead of pull?
# TODO: a teardown hook so I can client.disconnect() ?
# TODO: some kind of templating to make shown info configurable
# TODO: best practice to handle failures? just write to stderr?

from .. import bar, manager, utils
from mpd import MPDClient, CommandError
import atexit
import base


class Mpd(base._TextBox):
    """
        An mpd widget
    """
    defaults = manager.Defaults(
        ("font", "Arial", "Mpd widget font"),
        ("fontsize", None, "Mpd widget pixel size. Calculated if None."),
        ("padding", None, "Mpd widget padding. Calculated if None."),
        ("background", "000000", "Background colour"),
        ("foreground", "cccccc", "Foreground colour"),
        ("foreground_progress", "ffffff", "Foreground progress colour"),
        ("reconnect", False, "Choose if the widget should try to keep reconnect.")
    )

    def __init__(self, width=bar.CALCULATED, host='localhost', port=6600,
                 password=False, msg_nc='Mpd off', **config):
        """
            - host: host to connect to
            - port: port to connect to
            - password: password to use
            - msg_nc: which message to show when we're not connected
            - width: A fixed width, or bar.CALCULATED to calculate the width
            automatically (which is recommended).
        """
        self.host = host
        self.port = port
        self.password = password
        self.msg_nc = msg_nc
        self.inc = 2
        base._TextBox.__init__(self, " ", width, **config)
        self.client = MPDClient()
        self.connected = False
        self.connect()
        self.timeout_add(1, self.update)


    def connect(self, ifneeded=False):
        if self.connected:
            if not ifneeded:
                self.log.warning('Already connected. '
                    ' No need to connect again. '
                    'Maybe you want to disconnect first.')
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
        base._Widget._configure(self, qtile, bar)
        self.layout = self.drawer.textlayout(
            self.text, self.foreground, self.font, self.fontsize,
            markup=True)
        atexit.register(self.mpdDisconnect)

    def update(self):
        if not self.configured:
            return True
        if self.connect(True):
            try:
                status = self.client.status()
                song = self.client.currentsong()
                volume = status.get('volume', '-1')
                if song:
                    artist = ''
                    title = ''
                    if 'artist' in song:
                        artist = song['artist'].decode('utf-8')
                    if 'title' in song:
                        title = song['title'].decode('utf-8')

                    if 'artist' not in song and 'title' not in song:
                        playing = song.get('file', '??')
                    else:
                        playing = u'%s − %s' % (artist, title)

                    if status and status.get('time', None):
                        elapsed, total = status['time'].split(':')
                        percent = float(elapsed) / float(total)
                        progress = int(percent * len(playing))
                        playing = '<span color="%s">%s</span>%s' % (
                            utils.hex(self.foreground_progress),
                            utils.escape(playing[:progress].encode('utf-8')),
                            utils.escape(playing[progress:].encode('utf-8')))
                    else:
                        playing = utils.escape(playing)
                else:
                    playing = 'Stopped'

                playing = '%s [%s%%]' % (playing,
                                         volume if volume != '-1' else '?')
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
                        max(int(status['volume']) - self.inc, 0))
            elif button == 9:
                if status:
                    self.client.setvol(
                        min(int(status['volume']) + self.inc, 100))
        except Exception:
            self.log.exception('Mpd error on click')
