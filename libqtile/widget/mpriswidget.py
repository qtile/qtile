import gobject
import dbus

from dbus.mainloop.glib import DBusGMainLoop

import base
from .. import bar, manager

class Mpris(base._TextBox):
  """ A widget which displays the current clementine track/artist. """

  defaults = manager.Defaults(
      ("font", "Arial", "Mpd widget font"),
      ("fontsize", None, "Mpd widget pixel size. Calculated if None."),
      ("padding", None, "Mpd widget padding. Calculated if None."),
      ("background", "000000", "Background colour"),
      ("foreground", "ffffff", "Foreground colour")
    )

  def __init__(self, name="clementine", width=bar.CALCULATED,
               objname='org.mpris.clementine', **config):
    self.dbus_loop = DBusGMainLoop()
    self.objname = objname
    self.connected = False
    self.name = name
    self._connect()

    base._TextBox.__init__(self, " ", width, **config)

  def _connect(self):
    try:
      self.bus = dbus.SessionBus(mainloop=self.dbus_loop)
      self.player = self.bus.get_object(self.objname, '/Player')
      self.iface = dbus.Interface(self.player, 
                                  dbus_interface='org.freedesktop.MediaPlayer')
      
      # See: http://xmms2.org/wiki/MPRIS for info on signals and what they mean.
      self.iface.connect_to_signal("TrackChange", self.handle_track_change)
      self.iface.connect_to_signal("StatusChange", self.handle_status_change)
      self.connected = True
    except dbus.exceptions.DBusException:
      self.connected = False

  def handle_track_change(self, metadata):
    self.update()

  def handle_status_change(self, *args):
    self.update()

  def ensure_connected(f):
    def wrapper(*args, **kwargs):
      self = args[0]
      try:
        self.iface.GetMetadata()
      except (dbus.exceptions.DBusException, AttributeError):
        self._connect()
      
      return f(*args, **kwargs)
    return wrapper

  def _configure(self, qtile, bar):
    base._TextBox._configure(self, qtile, bar)
    self.timeout_add(1, self.update)

  @ensure_connected
  def update(self):
    if not self.connected:
      playing = ''
    elif not self.is_playing():
      playing = 'Stopped'
    else:
      try:
        metadata = self.iface.GetMetadata()
        playing = metadata["title"] + ' - ' + metadata["artist"]
      except dbus.exceptions.DBusException:
        self.connected = False
        playing = 'Stopped'

    if playing != self.text:
      self.text = playing
      self.bar.draw()

  @ensure_connected
  def is_playing(self):
    if self.connected:
      (playing,random,repeat,stop_after_last) = self.iface.GetStatus()
      return playing == 0
    else:
      return False

  def cmd_info(self):
    return dict(connected = self.connected,
                nowplaying = self.text, 
                isplaying = self.is_playing(),
               )

  def cmd_update(self):
    self.update()
    
if __name__ == "__main__":
  cl = Clementine()
  try:
    import gobject
    loop = gobject.MainLoop()
    loop.run()
  except KeyboardInterrupt:
    pass
  print "Is playing?", cl.is_playing()
