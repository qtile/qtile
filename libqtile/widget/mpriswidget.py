import dbus

# import base
# from .. import bar, manager

class Clementine(object):
  """ A widget which displays the current clementine track/artist. """
  def __init__(self, objname='org.mpris.clementine'):
    from dbus.mainloop.glib import DBusGMainLoop
    self.dbus_loop = DBusGMainLoop()

    self.bus = dbus.SessionBus(mainloop=self.dbus_loop)
    self.player = self.bus.get_object(objname, '/Player')
    self.iface = dbus.Interface(self.player, 
                                dbus_interface='org.freedesktop.MediaPlayer')
    
    # See: http://xmms2.org/wiki/MPRIS for info on signals and what they mean.
    self.iface.connect_to_signal("TrackChange", self.handle_track_change)
    self.iface.connect_to_signal("StatusChange", self.handle_status_change)

  def run(self):
    import gobject
    loop = gobject.MainLoop()
    loop.run()

  def metadata(self):
    return self.iface.GetMetadata()

  def _connect(self):
    root = self.bus.get_object('org.mpris.clementine', '/')
    rif = dbus.Interface(root, dbus_interface='org.freedesktop.MediaPlayer')

  def handle_track_change(self, metadata):
    self._connect()
    print metadata["title"], '-', metadata["artist"]

  def handle_status_change(self, *args):
    self._connect()
    print args

cl = Clementine()

try:
  cl.run()
except KeyboardInterrupt:
  pass
cl.metadata()
print 'returned'
