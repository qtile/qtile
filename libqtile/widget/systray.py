from .. import bar, hook, utils, manager, xcbq
import cairo
import base

import xcb
import struct


class Systray(base._Widget):
    """
        A widget that manage system tray
    """
    defaults = manager.Defaults(
                ('icon_size', 20, 'Icon width'),
            )
    def __init__(self, **config):
        base._Widget.__init__(self, bar.CALCULATED, **config)
        self.icons = {}

    def click(self, x, y):
        pass

    def calculate_width(self):
        width = len(self.icons) * self.icon_size
        return width

    def handle_client_message(self, event):
        atoms = self.qtile.conn.atoms

        opcode = xcb.xproto.ClientMessageData(event, 0, 20).data32[2]
        data = xcb.xproto.ClientMessageData(event, 12, 20)
        task = data.data32[2]

        conn = self.qtile.conn.conn
        parent = self.bar.window.window

        if opcode == atoms['_NET_SYSTEM_TRAY_OPCODE']:
            w = xcbq.Window(self.qtile.conn, task)
            self.icons[task] = w

            self.qtile.windowMap[task] = w

            w.handle_ConfigureNotify = self.handle_configure_notify
            w.handle_DestroyNotify = self.handle_destroy_notify
            w.handle_UnmapNotify = self.handle_destroy_notify

            conn.core.ReparentWindow(task, parent.wid, 0, 0)
            conn.core.ChangeWindowAttributes(
                    task, xcb.xproto.CW.EventMask,
                    [xcb.xproto.EventMask.Exposure|\
                     xcb.xproto.EventMask.StructureNotify])

            conn.flush()
            w.map()
        return False

    def handle_configure_notify(self, event):
        self.draw()
        return False

    def handle_destroy_notify(self, event):
        wid = event.window
        del(self.qtile.windowMap[wid])
        del(self.icons[wid])
        self.draw()
        return False

    def _configure_window(self, window, pos):
        conn = self.qtile.conn.conn
        window.configure(x=self.offset+(self.icon_size*pos),
                    y=0, width=self.icon_size,
                    height=self.icon_size)

    def _configure(self, qtile, bar):
        base._Widget._configure(self, qtile, bar)
        self.qtile = qtile
        self.bar = bar

        atoms = qtile.conn.atoms

        self.window = qtile.conn.create_window(-1, -1, 1, 1)
        qtile.windowMap[self.window.wid] = self.window


        self.window.handle_ClientMessage = self.handle_client_message

        qtile.conn.conn.core.SetSelectionOwner(self.window.wid,
                  atoms['_NET_SYSTEM_TRAY_S0'], xcb.CurrentTime)

        event = struct.pack('BBHII5I', 33, 32, 0, qtile.root.wid,
                            atoms['MANAGER'], 
                            xcb.CurrentTime, atoms['_NET_SYSTEM_TRAY_S0'],
                            self.window.wid, 0, 0)

        self.window.send_event(event)

    def draw(self):
        for pos, window in enumerate(self.icons.values()):
            self._configure_window(window, pos)
