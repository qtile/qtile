# -*- coding: utf-8 -*-
# depends on python-mpd


# TODO: check if UI hangs in case of network issues and such
# TODO: python-mpd supports idle proto, can widgets be push instead of pull?
# TODO: a teardown hook so I can client.disconnect() ?
# TODO: some kind of templating to make shown info configurable
# TODO: best practice to handle failures? just write to stderr?

from .. import hook, bar, manager
import base
from mpd import (MPDClient, CommandError)
from socket import error as SocketError

class Mpd(base._TextBox):
    """
        An mpd widget
    """
    defaults = manager.Defaults(
        ("font", "Arial", "Clock font"),
        ("fontsize", None, "Clock pixel size. Calculated if None."),
        ("padding", None, "Clock padding. Calculated if None."),
        ("background", "000000", "Background colour"),
        ("foreground", "ffffff", "Foreground colour")
    )
    def mpdConnect(self, con_id):
        """
            Simple wrapper to connect MPD.
        """
        try:
            self.client.connect(**con_id)
        except SocketError:
            return False
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

    def __init__(self, width=bar.CALCULATED, host='localhost', port=6600, password=False, **config):
        """
	    - host: host to connect to
	    - port: port to connect to
	    - password: password to use
            - width: A fixed width, or bar.CALCULATED to calculate the width
            automatically (which is recommended).
        """
        self.host = host
        self.port = port
        self.password = password
        base._TextBox.__init__(self, " ", width, **config)
        self.client = MPDClient()
        CON_ID = {'host':self.host, 'port':self.port}
        if not self.mpdConnect(CON_ID):
            print >> stderr, 'fail to connect MPD server.'
        if self.password:
            if not self.mpdAuth(self.password):
                print >> stderr, 'Error trying to pass auth.'
                client.disconnect()

    def _configure(self, qtile, bar):
        #TODO: don't do this if connection failed
        base._TextBox._configure(self, qtile, bar)
        hook.subscribe.tick(self.update)

    def update(self):
        song = self.client.currentsong()
        playing = "%s - %s" % (song['artist'], song['title'])
        if self.text != playing:
            self.text = playing
            self.bar.draw()
