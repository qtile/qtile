# Copyright (c) 2008, Aldo Cortesi. All rights reserved.
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

import marshal, sys
import Xlib
from Xlib import X, Xatom
import Xlib.protocol.event as event
import command, utils

class _Window(command.CommandObject):
    def __init__(self, window, qtile):
        self.window, self.qtile = window, qtile
        self.hidden = True
        window.change_attributes(event_mask=self._windowMask)
        self.x, self.y, self.width, self.height = None, None, None, None
        self.borderwidth = 0
        self.name = "<no name>"
        self.updateName()

    def updateName(self):
        try:
            self.name = self.window.get_wm_name()
            self.qtile.event.fire("window_name_change")
        except (Xlib.error.BadWindow, Xlib.error.BadValue):
            # This usually means the window has just been deleted, and a new
            # focus will be acquired shortly. We don't raise an event for this.
            pass

    def info(self):
        return dict(
            name = self.name,
            x = self.x,
            y = self.y,
            width = self.width,
            height = self.height,
            id = str(hex(self.window.id))
        )

    def notify(self):
        e = event.ConfigureNotify(
                window = self.window,
                event = self.window,
                x = self.x,
                y = self.y,
                width = self.width,
                height = self.height,
                border_width = self.borderwidth,
                override = False,
                above_sibling = X.NONE
        )
        self.window.send_event(e)

    def kill(self):
        if self.hasProtocol("WM_DELETE_WINDOW"):
            e = event.ClientMessage(
                    window = self.window,
                    client_type = self.qtile.display.intern_atom("WM_PROTOCOLS"),
                    data = [
                        # Use 32-bit format:
                        32,
                        # Must be exactly 20 bytes long:
                        [
                            self.qtile.display.intern_atom("WM_DELETE_WINDOW"),
                            X.CurrentTime,
                            0,
                            0,
                            0
                        ]
                    ]
            )
            self.window.send_event(e)
        else:
            self.window.kill_client()

    def hide(self):
        # We don't want to get the UnmapNotify for this unmap
        self.disableMask(X.StructureNotifyMask)
        self.window.unmap()
        self.resetMask()
        self.hidden = True

    def unhide(self):
        self.window.map()
        self.hidden = False

    def disableMask(self, mask):
        self.window.change_attributes(
            event_mask=self._windowMask&(~mask)
        )

    def resetMask(self):
        self.window.change_attributes(
            event_mask=self._windowMask
        )

    def place(self, x, y, width, height, border, borderColor):
        """
            Places the window at the specified location with the given size.
        """
        self.x, self.y, self.width, self.height = x, y, width, height
        self.window.configure(
            x=x,
            y=y,
            width=width,
            height=height,
            border_width=border
        )
        if borderColor is not None:
            self.window.change_attributes(
                border_pixel = borderColor
            )

    def focus(self, warp):
        if not self.hidden:
            self.window.set_input_focus(
                X.RevertToPointerRoot,
                X.CurrentTime
            )
            self.window.configure(
                stack_mode = X.Above
            )
            if warp:
                self.window.warp_pointer(0, 0)

    def hasProtocol(self, name):
        s = set()
        d = self.qtile.display
        for i in self.window.get_wm_protocols():
            s.add(d.get_atom_name(i))
        return name in s

    def setProp(self, name, data):
        self.window.change_property(
            self.qtile.atoms[name],
            self.qtile.atoms["python"],
            8,
            marshal.dumps(data)
        )

    def _select(self, name, sel):
        return None

    def cmd_info(self):
        return dict(
            id = self.window.id
        )



class Internal(_Window):
    """
        An internal window, that should not be managed by qtile.
    """
    _windowMask = X.StructureNotifyMask |\
                 X.PropertyChangeMask |\
                 X.EnterWindowMask |\
                 X.FocusChangeMask |\
                 X.ExposureMask |\
                 X.ButtonPressMask
    @classmethod
    def create(klass, qtile, background_pixel, x, y, width, height):
        win = qtile.root.create_window(
                    x, y, width, height, 0,
                    X.CopyFromParent, X.InputOutput,
                    X.CopyFromParent,
                    background_pixel = background_pixel,
                    event_mask = X.StructureNotifyMask | X.ExposureMask
               )
        i = Internal(win, qtile)
        i.place(x, y, width, height, 0, None)
        i.setProp("internal", True)
        return i

    def __repr__(self):
        return "Internal(%s)"%self.name


class Window(_Window):
    _windowMask = X.StructureNotifyMask |\
                 X.PropertyChangeMask |\
                 X.EnterWindowMask |\
                 X.FocusChangeMask
    group = None
    def handle_EnterNotify(self, e):
        self.group.focus(self, False)
        if self.group.screen and self.qtile.currentScreen != self.group.screen:
            self.qtile.toScreen(self.group.screen.index)

    def handle_ConfigureRequest(self, e):
        if self.group.screen:
            self.group.layout.configure(self)
            self.notify()

    def handle_PropertyNotify(self, e):
        if e.atom == Xatom.WM_TRANSIENT_FOR:
            print >> sys.stderr, "transient"
        elif e.atom == Xatom.WM_HINTS:
            print >> sys.stderr, "hints"
        elif e.atom == Xatom.WM_NORMAL_HINTS:
            print >> sys.stderr, "normal_hints"
        elif e.atom == Xatom.WM_NAME:
            self.updateName()
        else:
            print >> sys.stderr, e

    def _select(self, name, sel):
        if name == "group":
            if sel is None or sel == self.group.name:
                return self.group
        elif name == "layout":
            if sel is None:
                return self.group.layout
            else:
                return utils.lget(self.group.layouts, sel)
        elif name == "screen":
            if sel is None or (self.group.screen and sel == self.group.screen.index):
                return self.group.screen

    def __repr__(self):
        return "Window(%s)"%self.name

