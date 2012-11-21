import dbus

from dbus.mainloop.glib import DBusGMainLoop

import base
from .. import bar, manager


class Mpris(base._TextBox):
    """
    A widget which displays the current track/artist of your favorite MPRIS
    player. It should work with all players which implement a reasonably
    correct version of MPRIS, though I have only tested it with clementine.
    """

    defaults = manager.Defaults(
            ("font", "Arial", "Mpd widget font"),
            ("fontsize", None, "Mpd widget pixel size. Calculated if None."),
            ("padding", None, "Mpd widget padding. Calculated if None."),
            ("background", None, "Background colour"),
            ("foreground", "ffffff", "Foreground colour")
        )

    def __init__(self, name="clementine", width=bar.CALCULATED,
                 objname='org.mpris.clementine', **config):
        base._TextBox.__init__(self, " ", width, **config)

        # we need a main loop to get event signals
        # we just piggyback on qtile's main loop
        self.dbus_loop = DBusGMainLoop()
        self.bus = dbus.SessionBus(mainloop=self.dbus_loop)

        # watch for our player to start up
        deebus = self.bus.get_object(
            'org.freedesktop.DBus', '/org/freedesktop/DBus')
        deebus.connect_to_signal(
            "NameOwnerChanged", self.handle_name_owner_change)

        self.objname = objname
        self.connected = False
        self.name = name

        # try to connect for grins
        self._connect()
        self.timeout_add(1, self.update)

    def _connect(self):
        """ Try to connect to the player if it exists. """
        try:
            self.player = self.bus.get_object(self.objname, '/Player')
            self.iface = dbus.Interface(
                self.player, dbus_interface='org.freedesktop.MediaPlayer')
            # See: http://xmms2.org/wiki/MPRIS for info on signals
            # and what they mean.
            self.iface.connect_to_signal(
                "TrackChange", self.handle_track_change)
            self.iface.connect_to_signal(
                "StatusChange", self.handle_status_change)
            self.connected = True
        except dbus.exceptions.DBusException:
            self.connected = False

    def handle_track_change(self, metadata):
        self.update()

    def handle_status_change(self, *args):
        self.update()

    def handle_name_owner_change(self, name, old_owner, new_owner):
        if name == self.objname:
            if old_owner == '':
                # Our player started, so connect to it
                self._connect()
            elif new_owner == '':
                # It disconnected :-(
                self.connected = False
            self.update()

    def ensure_connected(f):
        """
        Tries to connect to the player. It *should* be succesful if the player
        is alive. """
        def wrapper(*args, **kwargs):
            self = args[0]
            try:
                self.iface.GetMetadata()
            except (dbus.exceptions.DBusException, AttributeError):
                # except AttributeError because
                # self.iface won't exist if we haven't
                # _connect()ed yet
                self._connect()
            return f(*args, **kwargs)
        return wrapper

    @ensure_connected
    def update(self):
        if not self.configured:
            return True
        if not self.connected:
            playing = ''
        elif not self.is_playing():
            playing = 'Stopped'
        else:
            try:
                metadata = self.iface.GetMetadata()

                # TODO: Make this configurable?
                playing = metadata["title"] + ' - ' + metadata["artist"]
            except dbus.exceptions.DBusException:
                self.connected = False
                playing = ''

        if playing != self.text:
            self.text = playing
            self.bar.draw()

    @ensure_connected
    def is_playing(self):
        """ Returns true if we are connected to the player and it is playing
        something, false otherwise. """
        if self.connected:
            (playing, random, repeat, stop_after_last) = self.iface.GetStatus()
            return playing == 0
        else:
            return False

    def cmd_info(self):
        """ What's the current state of the widget? """
        return dict(connected=self.connected,
                    nowplaying=self.text,
                    isplaying=self.is_playing(),
                )

    def cmd_update(self):
        """ Force the widget to update. Mostly used for testing. """
        self.update()

# vim: tabstop=4 shiftwidth=4 expandtab
