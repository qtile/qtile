from .. import bar, hook, utils, manager
import cairo
import base

import xcb
import struct


class Systray(base._Widget):
    """
        A widget that manage system tray
    """
    defaults = manager.Defaults()
    def __init__(self, **config):
        base._Widget.__init__(self, bar.CALCULATED, **config)

    def click(self, x, y):
        pass

    def calculate_width(self):
        return 50

    def _configure(self, qtile, bar):
        base._Widget._configure(self, qtile, bar)

        atoms = qtile.conn.atoms

        self.window = qtile.conn.create_window(-1, -1, 1, 1)
        qtile.windowMap[self.window.wid] = self.window

        def handle(event):
            print 'My Event', event
            return True

        self.window.handle_ClientMessage = handle
        self.window.handle_ConfigureNotify = handle
        self.window.handle_DestroyNotify = handle

        qtile.conn.conn.core.SetSelectionOwner(self.window.wid,
                  atoms['_NET_SYSTEM_TRAY_S0'], xcb.CurrentTime)

        event = struct.pack('BBHII5I', 33, 32, 0, qtile.root.wid,
                            atoms['MANAGER'], 
                            xcb.CurrentTime, atoms['_NET_SYSTEM_TRAY_S0'],
                            self.window.wid, 0, 0)

        self.window.send_event(event)

    def draw(self):
        pass
