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

from __future__ import annotations

import xcffib
from xcffib.xproto import ClientMessageData, ClientMessageEvent, EventMask, SetMode

from libqtile import bar
from libqtile.backend.x11 import window
from libqtile.confreader import ConfigError
from libqtile.widget import base

XEMBED_PROTOCOL_VERSION = 0


class Icon(window._Window):
    _window_mask = EventMask.StructureNotify | EventMask.PropertyChange | EventMask.Exposure

    def __init__(self, win, qtile, systray):
        window._Window.__init__(self, win, qtile)
        self.hidden = True
        self.systray = systray
        # win.get_name() may return None when apps provide a temporary window before the icon window
        # we need something in self.name in order to sort icons so we use the window's WID.
        self.name = win.get_name() or str(win.wid)
        self.update_size()
        self._wm_class: list[str] | None = None

    def __eq__(self, other):
        if not isinstance(other, Icon):
            return False

        return self.window.wid == other.window.wid

    def update_size(self):
        icon_size = self.systray.icon_size
        self.update_hints()

        width = self.hints.get("min_width", icon_size)
        height = self.hints.get("min_height", icon_size)

        width = max(width, icon_size)
        height = max(height, icon_size)

        if height > icon_size:
            width = width * icon_size // height
            height = icon_size

        self.width = width
        self.height = height
        return False

    def handle_PropertyNotify(self, e):  # noqa: N802
        name = self.qtile.core.conn.atoms.get_name(e.atom)
        if name == "_XEMBED_INFO":
            info = self.window.get_property("_XEMBED_INFO", unpack=int)
            if info and info[1]:
                self.systray.bar.draw()

        return False

    def handle_DestroyNotify(self, event):  # noqa: N802
        wid = event.window
        icon = self.qtile.windows_map.pop(wid)
        self.systray.tray_icons.remove(icon)
        self.systray.bar.draw()
        return False

    handle_UnmapNotify = handle_DestroyNotify  # noqa: N815


# Mypy doesn't like the inheritance of height and width as _Widget's
# properties are read only but _Window's have a getter and setter.
class Systray(base._Widget, window._Window):  # type: ignore[misc]
    """
    A widget that manages system tray.

    Only one Systray widget is allowed. Adding additional Systray
    widgets will result in a ConfigError.

    .. note::
        Icons will not render correctly where the bar/widget is
        drawn with a semi-transparent background. Instead, icons
        will be drawn with a transparent background.

        If using this widget it is therefore recommended to use
        a fully opaque background colour or a fully transparent
        one.
    """

    _instances = 0

    _window_mask = EventMask.StructureNotify | EventMask.Exposure

    orientations = base.ORIENTATION_BOTH

    supported_backends = {"x11"}

    defaults = [
        ("icon_size", 20, "Icon width"),
        ("padding", 5, "Padding between icons"),
    ]

    def __init__(self, **config):
        base._Widget.__init__(self, bar.CALCULATED, **config)
        self.add_defaults(Systray.defaults)
        self.tray_icons = []
        self.screen = 0
        self._name = config.get("name", "systray")
        self._wm_class: list[str] | None = None

    def calculate_length(self):
        if self.bar.horizontal:
            length = sum(i.width for i in self.tray_icons)
        else:
            length = sum(i.height for i in self.tray_icons)
        length += self.padding * len(self.tray_icons)
        return length

    def _configure(self, qtile, bar):
        base._Widget._configure(self, qtile, bar)

        if self.configured:
            return

        if Systray._instances > 0:
            raise ConfigError("Only one Systray can be used.")

        self.conn = conn = qtile.core.conn
        win = conn.create_window(-1, -1, 1, 1)
        window._Window.__init__(self, window.XWindow(conn, win.wid), qtile)
        qtile.windows_map[win.wid] = self

        # window._Window.__init__ overwrites the widget name so we need to restore it
        self.name = self._name

        # Even when we have multiple "Screen"s, we are setting up as the system
        # tray on a particular X display, that is the screen we need to
        # reference in the atom
        if qtile.current_screen:
            self.screen = qtile.current_screen.index
        self.bar = bar
        atoms = conn.atoms

        # We need tray to tell icons which visual to use.
        # This needs to be the same as the bar/widget.
        # This mainly benefits transparent bars.
        conn.conn.core.ChangeProperty(
            xcffib.xproto.PropMode.Replace,
            win.wid,
            atoms["_NET_SYSTEM_TRAY_VISUAL"],
            xcffib.xproto.Atom.VISUALID,
            32,
            1,
            [self.drawer._visual.visual_id],
        )

        conn.conn.core.SetSelectionOwner(
            win.wid, atoms[f"_NET_SYSTEM_TRAY_S{self.screen:d}"], xcffib.CurrentTime
        )
        data = [
            xcffib.CurrentTime,
            atoms[f"_NET_SYSTEM_TRAY_S{self.screen:d}"],
            win.wid,
            0,
            0,
        ]
        union = ClientMessageData.synthetic(data, "I" * 5)
        event = ClientMessageEvent.synthetic(
            format=32, window=qtile.core._root.wid, type=atoms["MANAGER"], data=union
        )
        qtile.core._root.send_event(event, mask=EventMask.StructureNotify)

        Systray._instances += 1

    def create_mirror(self):
        """
        Systray cannot be mirrored as we do not use a Drawer object to render icons.

        Return new, unconfigured instance so that, when the bar tries to configure it
        again, a ConfigError is raised.
        """
        return Systray()

    def handle_ClientMessage(self, event):  # noqa: N802
        atoms = self.conn.atoms

        opcode = event.type
        data = event.data.data32
        message = data[1]
        wid = data[2]

        parent = self.bar.window.window

        if opcode == atoms["_NET_SYSTEM_TRAY_OPCODE"] and message == 0:
            w = window.XWindow(self.conn, wid)
            icon = Icon(w, self.qtile, self)
            if icon not in self.tray_icons:
                self.tray_icons.append(icon)
                self.tray_icons.sort(key=lambda icon: icon.name)
                self.qtile.windows_map[wid] = icon

            self.conn.conn.core.ChangeSaveSet(SetMode.Insert, wid)
            self.conn.conn.core.ReparentWindow(wid, parent.wid, 0, 0)
            self.conn.conn.flush()

            info = icon.window.get_property("_XEMBED_INFO", unpack=int)

            if not info:
                self.bar.draw()
                return False

            if info[1]:
                self.bar.draw()

        return False

    def draw(self):
        _xoffset = self.offsetx if self.bar.horizontal else self.offsety
        _yoffset = self.offsety if self.bar.horizontal else self.offsetx
        xoffset = _xoffset + self.padding
        yoffset = self.bar.size // 2 - self.icon_size // 2 + _yoffset
        self.drawer.clear(self.background or self.bar.background)
        self.draw_at_default_position()

        for pos, icon in enumerate(self.tray_icons):
            icon.window.set_attribute(backpixmap=self.drawer.pixmap)
            if self.bar.horizontal:
                step = icon.width
                icon.place(xoffset, yoffset, icon.width, self.icon_size, 0, None)
            else:
                step = icon.height
                icon.place(yoffset, xoffset, icon.width, self.icon_size, 0, None)
            xoffset += step + self.padding

            if icon.hidden:
                icon.unhide()
                data = [
                    self.conn.atoms["_XEMBED_EMBEDDED_NOTIFY"],
                    xcffib.xproto.Time.CurrentTime,
                    0,
                    self.bar.window.wid,
                    XEMBED_PROTOCOL_VERSION,
                ]
                u = xcffib.xproto.ClientMessageData.synthetic(data, "I" * 5)
                event = xcffib.xproto.ClientMessageEvent.synthetic(
                    format=32, window=icon.wid, type=self.conn.atoms["_XEMBED"], data=u
                )
                self.window.send_event(event)

    def finalize(self):
        base._Widget.finalize(self)
        atoms = self.conn.atoms

        try:
            self.conn.conn.core.SetSelectionOwner(
                0,
                atoms[f"_NET_SYSTEM_TRAY_S{self.screen:d}"],
                xcffib.CurrentTime,
            )
            self.hide()

            root = self.qtile.core._root.wid
            for icon in self.tray_icons:
                self.conn.conn.core.ReparentWindow(icon.window.wid, root, 0, 0)
            self.conn.conn.flush()

            self.conn.conn.core.DestroyWindow(self.wid)
        except xcffib.ConnectionException:
            self.hidden = True  # Usually set in self.hide()

        del self.qtile.windows_map[self.wid]
        Systray._instances -= 1

    def info(self):
        info = window._Window.info(self)
        info["widget"] = base._Widget.info(self)
        return info
