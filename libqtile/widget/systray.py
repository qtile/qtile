from .. import bar, manager, xcbq, window
import base

import xcb
from xcb.xproto import EventMask, SetMode
import atexit
import struct


class Icon(window._Window):
    _windowMask = EventMask.StructureNotify |\
                  EventMask.Exposure

    def __init__(self, win, qtile, systray):
        window._Window.__init__(self, win, qtile)
        self.systray = systray
        self.width = self.height = systray.icon_size

    def handle_ConfigureNotify(self, event):
        icon_size = self.systray.icon_size
        self.updateHints()

        try:
            width, height = self.hints["min_width"], self.hints["min_height"]
        except KeyError:
            width, height = icon_size, icon_size

        if height > icon_size:
            new_width = width / height * icon_size
            height = icon_size
            width = new_width
        if height <= 0:
            width, height = icon_size, icon_size

        self.width, self.height = width, height
        self.window.set_attribute(backpixmap=self.systray.drawer.pixmap)
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
            try:
                w = xcbq.Window(self.qtile.conn, task)
                icon = Icon(w, self.qtile, self.systray)
                self.systray.icons[task] = icon
                self.qtile.windowMap[task] = icon

                # add icon window to the save-set, so it gets reparented
                # to the root window when qtile dies
                conn.core.ChangeSaveSet(SetMode.Insert, task)

                conn.core.ReparentWindow(task, parent.wid, 0, 0)
                conn.flush()
                w.map()
            except xcb.xproto.DrawableError:
                # The icon wasn't ready to be drawn yet... (NetworkManager does
                # this sometimes), so we just forget about it and wait for the
                # next event.
                pass
        return False


class Systray(base._Widget):
    """
        A widget that manage system tray
    """
    defaults = manager.Defaults(
                ('icon_size', 20, 'Icon width'),
                ('padding', 5, 'Padding between icons'),
                ('background', None, 'Background colour'),
            )

    def __init__(self, **config):
        base._Widget.__init__(self, bar.CALCULATED, **config)
        self.traywin = None
        self.icons = {}

    def button_press(self, x, y, button):
        pass

    def calculate_width(self):
        width = sum([i.width for i in self.icons.values()])
        width += self.padding * len(self.icons)
        return width

    def _configure(self, qtile, bar):
        base._Widget._configure(self, qtile, bar)
        self.qtile = qtile
        self.bar = bar
        atoms = qtile.conn.atoms
        win = qtile.conn.create_window(-1, -1, 1, 1)
        self.traywin = TrayWindow(win, self.qtile, self)
        qtile.windowMap[win.wid] = self.traywin
        qtile.conn.conn.core.SetSelectionOwner(
            win.wid,
            atoms['_NET_SYSTEM_TRAY_S0'],
            xcb.CurrentTime
        )
        event = struct.pack('BBHII5I', 33, 32, 0, qtile.root.wid,
                            atoms['MANAGER'],
                            xcb.CurrentTime, atoms['_NET_SYSTEM_TRAY_S0'],
                            win.wid, 0, 0)
        qtile.root.send_event(event, mask=EventMask.StructureNotify)

        # cleanup before exit
        atexit.register(self.cleanup)

    def draw(self):
        self.drawer.clear(self.background or self.bar.background)
        self.drawer.draw(self.offset, self.calculate_width())
        xoffset = self.padding
        for pos, icon in enumerate(self.icons.values()):
            icon.place(
                    self.offset + xoffset,
                    self.bar.height / 2 - self.icon_size / 2,
                    icon.width, self.icon_size,
                    0,
                    None
            )
            xoffset += icon.width + self.padding

    def cleanup(self):
        atoms = self.qtile.conn.atoms
        self.qtile.conn.conn.core.SetSelectionOwner(
            0,
            atoms['_NET_SYSTEM_TRAY_S0'],
            xcb.CurrentTime,
        )
        self.traywin.hide()
