# Copyright (c) 2010 Aldo Cortesi
# Copyright (c) 2010-2011 dequis
# Copyright (c) 2010, 2012 roger
# Copyright (c) 2011 Mounier Florian
# Copyright (c) 2011-2012, 2014 Tycho Andersen
# Copyright (c) 2012 dmpayton
# Copyright (c) 2012-2013 Craig Barnes
# Copyright (c) 2013 hbc
# Copyright (c) 2013 Tao Sauvage
# Copyright (c) 2014 Sean Vig
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

from __future__ import division

from .. import bar, xcbq, window
from . import base

import xcffib
from xcffib.xproto import (ClientMessageEvent, ClientMessageData, EventMask,
                           SetMode)

XEMBED_PROTOCOL_VERSION = 0


class Icon(window._Window):
    _windowMask = EventMask.StructureNotify | \
        EventMask.PropertyChange | \
        EventMask.Exposure

    def __init__(self, win, qtile, systray):
        window._Window.__init__(self, win, qtile)
        self.systray = systray
        self.update_size()

    def update_size(self):
        icon_size = self.systray.icon_size
        self.update_hints()

        try:
            width = self.hints["min_width"]
            height = self.hints["min_height"]
        except KeyError:
            width = icon_size
            height = icon_size

        if height > icon_size:
            width = width * icon_size // height
            height = icon_size
        if height <= 0:
            width = icon_size
            height = icon_size

        self.width = width
        self.height = height
        return False

    def handle_PropertyNotify(self, e):
        name = self.qtile.conn.atoms.get_name(e.atom)
        if name == "_XEMBED_INFO":
            info = self.window.get_property('_XEMBED_INFO', unpack=int)
            if info and info[1]:
                self.systray.bar.draw()

        return False

    def handle_DestroyNotify(self, event):
        wid = event.window
        del(self.qtile.windowMap[wid])
        del(self.systray.icons[wid])
        self.systray.bar.draw()
        return False

    handle_UnmapNotify = handle_DestroyNotify


class Systray(window._Window, base._Widget):
    """A widget that manages system tray"""

    _windowMask = EventMask.StructureNotify | \
        EventMask.Exposure

    orientations = base.ORIENTATION_HORIZONTAL

    defaults = [
        ('icon_size', 20, 'Icon width'),
        ('padding', 5, 'Padding between icons'),
    ]

    def __init__(self, **config):
        base._Widget.__init__(self, bar.CALCULATED, **config)
        self.add_defaults(Systray.defaults)
        self.icons = {}
        self.screen = 0

    def calculate_length(self):
        width = sum(i.width for i in self.icons.values())
        width += self.padding * len(self.icons)
        return width

    def _configure(self, qtile, bar):
        base._Widget._configure(self, qtile, bar)
        win = qtile.conn.create_window(-1, -1, 1, 1)
        window._Window.__init__(self, xcbq.Window(qtile.conn, win.wid), qtile)
        qtile.windowMap[win.wid] = self

        # Even when we have multiple "Screen"s, we are setting up as the system
        # tray on a particular X display, that is the screen we need to
        # reference in the atom
        if qtile.current_screen:
            self.screen = qtile.current_screen.index
        self.bar = bar
        atoms = qtile.conn.atoms

        qtile.conn.conn.core.SetSelectionOwner(
            win.wid,
            atoms['_NET_SYSTEM_TRAY_S{:d}'.format(self.screen)],
            xcffib.CurrentTime
        )
        data = [
            xcffib.CurrentTime,
            atoms['_NET_SYSTEM_TRAY_S{:d}'.format(self.screen)],
            win.wid, 0, 0
        ]
        union = ClientMessageData.synthetic(data, "I" * 5)
        event = ClientMessageEvent.synthetic(
            format=32,
            window=qtile.root.wid,
            type=atoms['MANAGER'],
            data=union
        )
        qtile.root.send_event(event, mask=EventMask.StructureNotify)

    def handle_ClientMessage(self, event):
        atoms = self.qtile.conn.atoms

        opcode = event.type
        data = event.data.data32
        message = data[1]
        wid = data[2]

        conn = self.qtile.conn.conn
        parent = self.bar.window.window

        if opcode == atoms['_NET_SYSTEM_TRAY_OPCODE'] and message == 0:
            w = xcbq.Window(self.qtile.conn, wid)
            icon = Icon(w, self.qtile, self)
            self.icons[wid] = icon
            self.qtile.windowMap[wid] = icon

            conn.core.ChangeSaveSet(SetMode.Insert, wid)
            conn.core.ReparentWindow(wid, parent.wid, 0, 0)
            conn.flush()

            info = icon.window.get_property('_XEMBED_INFO', unpack=int)

            if not info:
                self.bar.draw()
                return False

            if info[1]:
                self.bar.draw()

        return False

    def draw(self):
        xoffset = self.padding
        self.drawer.clear(self.background or self.bar.background)
        self.drawer.draw(offsetx=self.offset, width=self.length)
        for pos, icon in enumerate(self.icons.values()):
            icon.window.set_attribute(backpixmap=self.drawer.pixmap)
            icon.place(
                self.offset + xoffset,
                self.bar.height // 2 - self.icon_size // 2,
                icon.width, self.icon_size,
                0,
                None
            )
            if icon.hidden:
                icon.unhide()
                data = [
                    self.qtile.conn.atoms["_XEMBED_EMBEDDED_NOTIFY"],
                    xcffib.xproto.Time.CurrentTime,
                    0,
                    self.bar.window.window.wid,
                    XEMBED_PROTOCOL_VERSION
                ]
                u = xcffib.xproto.ClientMessageData.synthetic(data, "I" * 5)
                event = xcffib.xproto.ClientMessageEvent.synthetic(
                    format=32,
                    window=icon.window.wid,
                    type=self.qtile.conn.atoms["_XEMBED"],
                    data=u
                )
                self.window.send_event(event)

            xoffset += icon.width + self.padding

    def finalize(self):
        base._Widget.finalize(self)
        atoms = self.qtile.conn.atoms
        self.qtile.conn.conn.core.SetSelectionOwner(
            0,
            atoms['_NET_SYSTEM_TRAY_S{:d}'.format(self.screen)],
            xcffib.CurrentTime,
        )
        self.hide()
