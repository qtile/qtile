# -*- coding: utf-8 -*-
# depends on python-mpd


# TODO: check if UI hangs in case of network issues and such
# TODO: python-mpd supports idle proto, can widgets be push instead of pull?
# TODO: a teardown hook so I can client.disconnect() ?
# TODO: some kind of templating to make shown info configurable
# TODO: best practice to handle failures? just write to stderr?

from socket import error as SocketError
import sys

from .. import bar, manager, utils
import base
from mpd import MPDClient, CommandError, ConnectionError, ProtocolError


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
        ("foreground_progress", "ffffff", "Foreground progress colour")
    )

    def __init__(self, width=bar.CALCULATED, host='localhost', port=6600,
                 password=False, msg_nc='NC', **config):
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

    def connect(self, ifneeded=False):
        if self.connected:
            if not ifneeded:
                print >> sys.stderr, (
                    'Already connected. '
                    ' No need to connect again. '
                    'Maybe you want to disconnect first.')
            return True
        CON_ID = {'host': self.host, 'port': self.port}
        if not self.mpdConnect(CON_ID):
            print >> sys.stderr, 'Cannot connect to MPD server.'
        if self.password:
            if not self.mpdAuth(self.password):
                print >> sys.stderr, 'Authentication failed.  Disconnecting'
                self.client.disconnect()
        return self.connected

    def mpdConnect(self, con_id):
        """
            Simple wrapper to connect MPD.
        """
        try:
            self.client.connect(**con_id)
        except SocketError:
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
        self.timeout_add(1, self.update)

    def update(self):
        if not self.connect(True):
            return False
        try:
            status = self.client.status()
            song = self.client.currentsong()
            if song:
                artist = ''
                title = ''
                if 'artist' in song:
                    artist = song['artist']
                if 'title' in song:
                    title = song['title']
                if status:
                    elapsed, total = status['time'].split(':')
                    percent = float(elapsed) / float(total)

                    volume = status['volume']
                    total = len(artist) + len(title) + 3
                    progress = int(percent * total)
                    playing = '%s - %s' % (artist, title)
                    playing = '<span color="%s">%s</span>%s [%s%%]' % (
                        utils.hex(self.foreground_progress),
                        utils.escape(playing[:progress]),
                        utils.escape(playing[progress:]),
                        volume)
            else:
                playing = ''
        except (SocketError, ProtocolError, ConnectionError), e:
            print ("Got error during query. "
                   " Disconnecting.  Error was: %s" % str(e))
            playing = self.msg_nc
            self.mpdDisconnect()
        if self.text != playing:
            self.text = playing
            self.bar.draw()

        return True

    def click(self, x, y, button):
        status = self.client.status()
        if button == 1:
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
                self.client.setvol(max(int(status['volume']) - self.inc, 0))
        elif button == 9:
            if status:
                self.client.setvol(min(int(status['volume']) + self.inc, 100))
