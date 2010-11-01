from .. import bar, hook, utils, manager, xcbq, window
import cairo
import base

import xcb
from xcb.xproto import EventMask
import struct


class Icon(window._Window):
    _windowMask = EventMask.StructureNotify |\
                  EventMask.Exposure
    def __init__(self, win, qtile, systray):
        window._Window.__init__(self, win, qtile)
        self.systray = systray

    def _configure_icon(self, pos):
        window.configure(x=self.offset+(self.icon_size*pos),
                    y=0, width=self.icon_size,
                    height=self.icon_size)

    def handle_ConfigureNotify(self, event):
        self.systray.draw()
        return False

    def handle_DestroyNotify(self, event):
        wid = event.window
        del(self.qtile.windowMap[wid])
        del(self.systray.icons[wid])
        self.systray.draw()
        return False

    handle_UnmapNotify = handle_DestroyNotify


class TrayWindow(window._Window):
    _windowMask = EventMask.StructureNotify |\
                  EventMask.Exposure
    def __init__(self, win, qtile, systray):
        window._Window.__init__(self, win, qtile)
        self.systray = systray

    def handle_ClientMessage(self, event):
        atoms = self.qtile.conn.atoms

        opcode = xcb.xproto.ClientMessageData(event, 0, 20).data32[2]
        data = xcb.xproto.ClientMessageData(event, 12, 20)
        task = data.data32[2]

        conn = self.qtile.conn.conn
        parent = self.systray.bar.window.window

        if opcode == atoms['_NET_SYSTEM_TRAY_OPCODE']:
            w = xcbq.Window(self.qtile.conn, task)
            icon = Icon(w, self.qtile, self.systray)
            self.systray.icons[task] = icon
            self.qtile.windowMap[task] = icon
            conn.core.ReparentWindow(task, parent.wid, 0, 0)
            conn.flush()
            w.map()
        return False


class Systray(base._Widget):
    """
        A widget that manage system tray
    """
    defaults = manager.Defaults(
                ('icon_size', 20, 'Icon width'),
                ('padding', 5, 'Padding between icons'),
            )
    def __init__(self, **config):
        base._Widget.__init__(self, bar.CALCULATED, **config)
        self.icons = {}

    def click(self, x, y):
        pass

    def calculate_width(self):
        width = len(self.icons) * (self.icon_size + self.padding) + self.padding
        return width

    def _configure(self, qtile, bar):
        base._Widget._configure(self, qtile, bar)
        self.qtile = qtile
        self.bar = bar
        atoms = qtile.conn.atoms
        win = qtile.conn.create_window(-1, -1, 1, 1)
        intwin = TrayWindow(win, self.qtile, self)
        qtile.windowMap[win.wid] = intwin
        qtile.conn.conn.core.SetSelectionOwner(
            win.wid,
            atoms['_NET_SYSTEM_TRAY_S0'],
            xcb.CurrentTime
        )
        event = struct.pack('BBHII5I', 33, 32, 0, qtile.root.wid,
                            atoms['MANAGER'], 
                            xcb.CurrentTime, atoms['_NET_SYSTEM_TRAY_S0'],
                            win.wid, 0, 0)

        win.send_event(event)

    def draw(self):
        for pos, icon in enumerate(self.icons.values()):
            icon.place(
                    self.offset + (self.icon_size + self.padding)*pos + self.padding,
                    self.bar.height/2 - self.icon_size/2, 
                    self.icon_size, self.icon_size,
                    0,
                    None
            )
            
