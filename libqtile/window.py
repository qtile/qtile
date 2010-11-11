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

import sys, struct, contextlib
import xcb.xcb
from xcb.xproto import EventMask, StackMode
import xcb.xproto
import command, utils
import hook
import xcbq


# ICCM Constants
NoValue = 0x0000
XValue = 0x0001
YValue = 0x0002
WidthValue = 0x0004
HeightValue = 0x0008
AllValues = 0x000F
XNegative = 0x0010
YNegative = 0x0020
USPosition = (1 << 0)
USSize = (1 << 1)
PPosition = (1 << 2)
PSize = (1 << 3)
PMinSize = (1 << 4)
PMaxSize = (1 << 5)
PResizeInc = (1 << 6)
PAspect = (1 << 7)
PBaseSize = (1 << 8)
PWinGravity = (1 << 9)
PAllHints = (PPosition|PSize|PMinSize|PMaxSize|PResizeInc|PAspect)
InputHint = (1 << 0)
StateHint = (1 << 1)
IconPixmapHint = (1 << 2)
IconWindowHint = (1 << 3)
IconPositionHint = (1 << 4)
IconMaskHint = (1 << 5)
WindowGroupHint = (1 << 6)
MessageHint = (1 << 7)
UrgencyHint	= (1 << 8)
AllHints = (InputHint|StateHint|IconPixmapHint|IconWindowHint|
            IconPositionHint|IconMaskHint|WindowGroupHint|MessageHint|
            UrgencyHint)
WithdrawnState = 0

DontCareState = 0
NormalState = 1
ZoomState = 2
IconicState = 3
InactiveState = 4

RectangleOut = 0
RectangleIn = 1
RectanglePart = 2
VisualNoMask = 0x0
VisualIDMask = 0x1
VisualScreenMask = 0x2
VisualDepthMask = 0x4
VisualClassMask = 0x8
VisualRedMaskMask = 0x10
VisualGreenMaskMask = 0x20
VisualBlueMaskMask = 0x40
VisualColormapSizeMask = 0x80
VisualBitsPerRGBMask = 0x100
VisualAllMask = 0x1FF
ReleaseByFreeingColormap = 1
BitmapSuccess = 0
BitmapOpenFailed = 1
BitmapFileInvalid = 2
BitmapNoMemory = 3
XCSUCCESS = 0
XCNOMEM = 1
XCNOENT = 2


class _Window(command.CommandObject):
    def __init__(self, window, qtile):
        self.window, self.qtile = window, qtile
        self.hidden = True
        window.set_attribute(eventmask=self._windowMask)
        self.x, self.y, self.width, self.height = None, None, None, None
        self.borderwidth = 0
        self.bordercolor = None
        self.name = "<no name>"
        self.state = "normal"
        self.window_type = "normal"
        g = self.window.get_geometry()
        self._floating = False
        self._float_info = {
            'x': g.x, 'y': g.y,
            'w': g.width, 'h': g.height
            }

        self.hints = {
            'input': True,
            'state': NormalState, #Normal state
            'icon_pixmap': None,
            'icon_window': None,
            'icon_x': 0,
            'icon_y': 0,
            'icon_mask': 0,
            'window_group': None,
            'urgent': False,
            }
        self.updateHints()

    def updateName(self):
        self.name = self.window.get_name()
        hook.fire("window_name_change")

    def updateHints(self):
        """
            update the local copy of the window's WM_HINTS
            http://tronche.com/gui/x/icccm/sec-4.html#WM_HINTS
        """
        h = self.window.get_wm_hints()

        # FIXME
        # h values
        #{
        #    'icon_pixmap': 4194337,
        #    'icon_window': 0,
        #    'icon_mask': 4194340,
        #    'icon_y': 0,
        #    'input': 1,
        #    'icon_x': 0,
        #    'window_group': 4194305
        #    'initial_state': 1,
        #    'flags': set(['StateHint',
        #                  'IconMaskHint',
        #                  'WindowGroupHint',
        #                  'InputHint',
        #                  'UrgencyHint',
        #                  'IconPixmapHint']),
        #}

        if h and 'UrgencyHint' in h['flags']:
            self.hints['urgent'] = True
            hook.fire('client_urgent_hint_changed', self)
        elif self.urgent:
            self.hints['urgent'] = False
            hook.fire('client_urgent_hint_changed', self)

        return

    @property
    def urgent(self):
        return self.hints['urgent']

    def info(self):
        return dict(
            name = self.name,
            x = self.x,
            y = self.y,
            width = self.width,
            height = self.height,
            id = self.window.wid,
            floating = self._floating,
            float_info = self._float_info
        )

    def setState(self, val):
        if val in self.POSSIBLE_STATES:
            self.state = val

    def getState(self, val):
        return self.state == val

    def setOpacity(self, opacity):
        if 0.0 <= opacity <= 1.0:
            real_opacity = int(opacity * 0xffffffff)
            self.window.set_property('_NET_WM_WINDOW_OPACITY', real_opacity)
        else:
            return

    def getOpacity(self):
        opacity = self.window.get_property(
            self.qtile.display.get_atom('_NET_WM_WINDOW_OPACITY'),
            Xatom.CARDINAL,
            0,
            32
            )
        if not opacity:
            return 1.0
        else:
            value = opacity.value[0]
            as_float = round(
                (float(value)/0xffffffff),
                2  #2 decimal places
                )
            return as_float

    opacity = property(getOpacity, setOpacity)

    def notify(self):
        # Having to do it this way is goddamn awful.
        vals = [
            22, # ConfigureNotifyEvent
            0,
            self.window.wid,
            self.window.wid,
            xcb.xproto.Window._None,
            self.x,
            self.y,
            self.width,
            self.height,
            self.borderwidth,
            False
        ]
        self.window.send_event(
            struct.pack(
                'B1xHLLLhhHHHB5x',
                *vals
            ),
            xcb.xproto.EventMask.StructureNotify
        )

    def kill(self):
        if "WM_DELETE_WINDOW" in self.window.get_wm_protocols():
            #e = event.ClientMessage(
            #        window = self.window,
            #        client_type = self.qtile.display.intern_atom("WM_PROTOCOLS"),
            #        data = [
            #            # Use 32-bit format:
            #            32,
            #            # Must be exactly 20 bytes long:
            #            [
            #                self.qtile.display.intern_atom("WM_DELETE_WINDOW"),
            #                X.CurrentTime,
            #                0,
            #                0,
            #                0
            #            ]
            #        ]
            #)
            vals = [
                33, # ClientMessageEvent
                32, # Format
                0,
                self.window.wid,
                self.qtile.conn.atoms["WM_PROTOCOLS"],
                self.qtile.conn.atoms["WM_DELETE_WINDOW"],
                xcb.xproto.Time.CurrentTime,
                0,
                0,
                0,
            ]
            e = struct.pack('BBHII5I', *vals)
            self.window.send_event(e)
        else:
            self.window.kill_client()

    def hide(self):
        # We don't want to get the UnmapNotify for this unmap
        with self.disableMask(xcb.xproto.EventMask.StructureNotify):
            self.window.unmap()
        self.hidden = True

    def unhide(self):
        self.window.map()
        self.hidden = False

    @contextlib.contextmanager
    def disableMask(self, mask):
        self._disableMask(mask)
        yield
        self._resetMask()

    def _disableMask(self, mask):
        self.window.set_attribute(
            eventmask=self._windowMask&(~mask)
        )

    def _resetMask(self):
        self.window.set_attribute(
            eventmask=self._windowMask
        )

    def place(self, x, y, width, height, borderwidth, bordercolor, above=False):
        """
            Places the window at the specified location with the given size.
        """
        self.x, self.y, self.width, self.height = x, y, width, height
        self.borderwidth, self.bordercolor = borderwidth, bordercolor
        kwarg = dict(
            x=x,
            y=y,
            width=width,
            height=height,
            borderwidth=borderwidth,
            )
        if above:
            kwarg['stackmode'] = StackMode.Above
        self.window.configure(**kwarg)
        if bordercolor is not None:
            self.window.set_attribute(
                borderpixel = bordercolor
            )

    def focus(self, warp):
        if not self.hidden and self.hints['input']:
            self.window.set_input_focus()
            if warp:
                self.window.warp_pointer(0, 0)
        hook.fire("client_focus", self)

    def _items(self, name, sel):
        return None

    def _select(self, name, sel):
        return None

    def cmd_info(self):
        """
            Returns a dictionary of info for this object.
        """
        return self.info()

    def cmd_inspect(self):
        """
            Tells you more than you ever wanted to know about a window.
        """
        a = self.window.get_attributes()
        attrs = {
            "backing_store": a.backing_store,
            "visual": a.visual,
            "class": a._class,
            "bit_gravity": a.bit_gravity,
            "win_gravity": a.win_gravity,
            "backing_planes": a.backing_planes,
            "backing_pixel": a.backing_pixel,
            "save_under": a.save_under,
            "map_is_installed": a.map_is_installed,
            "map_state": a.map_state,
            "override_redirect": a.override_redirect,
            #"colormap": a.colormap,
            "all_event_masks": a.all_event_masks,
            "your_event_mask": a.your_event_mask,
            "do_not_propagate_mask": a.do_not_propagate_mask
        }
        props = self.window.list_properties()
        normalhints = self.window.get_wm_normal_hints()
        hints = self.window.get_wm_hints()
        protocols = []
        for i in self.window.get_wm_protocols():
            protocols.append(i)

        state = self.window.get_wm_state()

        return dict(
            attributes=attrs,
            properties=props,
            name = self.window.get_name(),
            wm_class = self.window.get_wm_class(),
            wm_window_role = self.window.get_wm_window_role(),
            wm_type = self.window.get_wm_type(),
            wm_transient_for = self.window.get_wm_transient_for(),
            protocols = protocols,
            wm_icon_name = self.window.get_wm_icon_name(),
            wm_client_machine = self.window.get_wm_client_machine(),
            normalhints = normalhints,
            hints = hints,
            state = state,
            float_info = self._float_info
        )


class Internal(_Window):
    """
        An internal window, that should not be managed by qtile.
    """
    _windowMask = EventMask.StructureNotify |\
                  EventMask.PropertyChange |\
                  EventMask.EnterWindow |\
                  EventMask.FocusChange |\
                  EventMask.Exposure |\
                  EventMask.ButtonPress |\
                  EventMask.KeyPress
    @classmethod
    def create(klass, qtile, x, y, width, height, opacity=1.0):
        win = qtile.conn.create_window(
                    x, y, width, height
              )
        win.set_property("QTILE_INTERNAL", 1)
        i = Internal(win, qtile)
        i.place(x, y, width, height, 0, None)
        i.opacity = opacity
        return i

    def __repr__(self):
        return "Internal(%s)"%self.name


class Static(_Window):
    """
        An internal window, that should not be managed by qtile.
    """
    _windowMask = EventMask.StructureNotify |\
                  EventMask.PropertyChange |\
                  EventMask.EnterWindow |\
                  EventMask.FocusChange |\
                  EventMask.Exposure
    def __init__(self, win, qtile, screen, x=None, y=None, width=None, height=None):
        _Window.__init__(self, win, qtile)
        self.updateName()
        self.conf_x, self.conf_y = x, y
        self.conf_width, self.conf_height = width, height
        self.x, self.y, self.width, self.height = x or 0, y or 0, width or 0, height or 0
        self.screen = screen
        if None not in (x, y, width, height):
            self.place(x, y, width, height, 0, 0)

    def handle_ConfigureRequest(self, e):
        cw = xcb.xproto.ConfigWindow
        # x = self.conf_x
        # y = self.conf_y
        # width = self.conf_width
        # height = self.conf_height

        if self.conf_x is None and e.value_mask & cw.X:
            self.x = e.x
        if self.conf_y is None and e.value_mask & cw.Y:
            self.y = e.y
        if self.conf_width is None and e.value_mask & cw.Width:
            self.width = e.width
        if self.conf_height is None and e.value_mask & cw.Height:
            self.height = e.height

        self.place(
            self.screen.x + self.x,
            self.screen.y + self.y,
            self.width,
            self.height,
            self.borderwidth,
            self.bordercolor
        )
        self.notify()
        return False

    def __repr__(self):
        return "Static(%s)"%self.name


class Window(_Window):
    _windowMask = EventMask.StructureNotify |\
                  EventMask.PropertyChange |\
                  EventMask.EnterWindow |\
                  EventMask.FocusChange
    # Set when this object is being retired.
    defunct = False
    _group = None

    def __init__(self, window, qtile):
        _Window.__init__(self, window, qtile)
        self.updateName()
        # add to group by position according to _NET_WM_DESKTOP property
        index = window.get_wm_desktop()
        if index and index < len(qtile.groups):
            group = qtile.groups[index]
            group.add(self)
            if group != qtile.currentScreen.group:
                self.hide()

    @property
    def group(self):
        return self._group

    @group.setter
    def group(self, group):
        if group:
            self.window.set_property("_NET_WM_DESKTOP",
                self.qtile.groups.index(group))
        self._group = group

    @property
    def floating(self):
        return self._floating

    @floating.setter
    def floating(self, value):
        if self._floating and not value:
            self.disablefloating()
        elif not self._floating and value:
            self.enablefloating()

    def static(self, screen, x=None, y=None, width=None, height=None):
        """
            Makes this window a static window, attached to a Screen. If any of
            the arguments are left unspecified, the values given by the window
            itself are used instead. So, for a window that's aware of its
            appropriate size and location (like dzen), you don't have to
            specify anything.
        """
        self.defunct = True
        screen = self.qtile.screens[screen]
        if self.group:
            self.group.remove(self)
        s = Static(self.window, self.qtile, screen, x, y, width, height)
        self.qtile.windowMap[self.window.wid] = s
        hook.fire("client_managed", s)
        return s

    def _reconfigure_floating(self):
        self.place(self.x,
                   self.y,
                   self.width,
                   self.height,
                   self.borderwidth,
                   self.bordercolor,
                   above=True,
                   )
        self.notify()
        if not self._floating:
            self._floating = True
            if self.group: # may be not, if it's called from hook
                self.group.layout_remove(self)
                self.group.layoutAll()

    def movefloating(self, x, y):
        self.x += x
        self.y += y
        self._reconfigure_floating()

    def resizefloating(self, x, y):
        self.width += x
        self.height += y
        self._reconfigure_floating()

    def setsizefloating(self, w, h):
        self.width = w
        self.height = h
        self._reconfigure_floating()

    def setposfloating(self, x, y):
        self.x = max(x, 0)
        self.y = max(y, 0)
        self._reconfigure_floating()

    def getsize(self):
        return self.width, self.height

    def getposition(self):
        return self.x, self.y

    def togglefloating(self):
        if self.floating:
            self.disablefloating()
        else:
            self._reconfigure_floating()

    def enablefloating(self):
        if not self._floating:
            self.x = self._float_info['x']
            self.y = self._float_info['y']
            self.width = self._float_info['w']
            self.height = self._float_info['h']
            self._reconfigure_floating()

    def disablefloating(self):
        if self._floating:
            self._floating = False
            self._float_info['x'] = self.x
            self._float_info['y'] = self.y
            self._float_info['w'] = self.width
            self._float_info['h'] = self.height
            self.group.layout_add(self)
            self.group.layoutAll()

    def togroup(self, groupName):
        """
            Move window to a specified group.
        """
        group = self.qtile.groupMap.get(groupName)
        if group is None:
            raise command.CommandError("No such group: %s"%groupName)
        if self.group is not group:
            if self.group:
                self.hide()
                self.group.remove(self)
            group.add(self)

    def match(self, wname=None, wmclass=None, role=None):
        """
            Match window against given attributes.

            - wname matches against the window name or title, that is,
            either `_NET_WM_VISIBLE_NAME`, `_NET_WM_NAME`, `WM_NAME`.

            - wmclass matches against any of the two values in the
            `WM_CLASS` property

            - role matches against the `WM_WINDOW_ROLE` property
        """
        if not (wname or wmclass or role):
            raise TypeError, "Either a name, a wmclass or a role must be specified"

        if wname and wname != self.name:
            return False

        cliclass = self.window.get_wm_class()
        if wmclass and cliclass and not wmclass in cliclass:
            return False

        clirole = self.window.get_wm_window_role()
        if role and clirole and role != clirole:
            return False
        return True

    def handle_EnterNotify(self, e):
        hook.fire("client_mouse_enter", self)
        if self.group.currentWindow != self:
            self.group.focus(self, False)
        if self.group.screen and self.qtile.currentScreen != self.group.screen:
            self.qtile.toScreen(self.group.screen.index)
        return True

    def handle_ConfigureRequest(self, e):
        cw = xcb.xproto.ConfigWindow
        if e.value_mask & cw.X:
            self.x = e.x
        if e.value_mask & cw.Y:
            self.y = e.y
        if e.value_mask & cw.Width:
            self.width = e.width
        if e.value_mask & cw.Height:
            self.height = e.height
        if self.group and self.group.screen:
            self.place(
                self.x,
                self.y,
                self.width,
                self.height,
                self.borderwidth,
                self.bordercolor
            )
            self.notify()
        return False

    def handle_PropertyNotify(self, e):
        name = self.qtile.conn.atoms.get_name(e.atom)
        if name == "WM_TRANSIENT_FOR":
            pass
        elif name == "WM_HINTS":
            self.updateHints()
        elif name == "WM_NORMAL_HINTS":
            pass
        elif name == "WM_NAME":
            self.updateName()
        elif name == "_NET_WM_NAME":
            self.updateName()
        elif name == "_NET_WM_VISIBLE_NAME":
            self.updateName()
        elif name == "_NET_WM_WINDOW_OPACITY":
            pass
        elif name == "WM_PROTOCOLS":
            pass
        elif self.qtile.debug:
            print >> sys.stderr, "Unknown window property: ", name
        return False

    def _items(self, name):
        if name == "group":
            return True, None
        elif name == "layout":
            return True, range(len(self.group.layouts))
        elif name == "screen":
            return True, None

    def _select(self, name, sel):
        if name == "group":
            return self.group
        elif name == "layout":
            if sel is None:
                return self.group.layout
            else:
                return utils.lget(self.group.layouts, sel)
        elif name == "screen":
            return self.group.screen

    def __repr__(self):
        return "Window(%s)"%self.name

    def cmd_static(self, screen, x, y, width, height):
        self.static(screen, x, y, width, height)

    def cmd_kill(self):
        """
            Kill this window. Try to do this politely if the client support
            this, otherwise be brutal.
        """
        self.kill()

    def cmd_togroup(self, groupName):
        """
            Move window to a specified group.

            Examples:

                togroup("a")
        """
        self.togroup(groupName)

    def cmd_move_floating(self, x, y):
        self.movefloating(x, y)

    def cmd_resize_floating(self, x, y):
        self.resizefloating(x, y)

    def cmd_set_position_floating(self, x, y):
        self.setposfloating(x, y)

    def cmd_set_size_floating(self, w, h):
        self.setsizefloating(w, h)

    def cmd_get_position(self):
        return self.getposition()

    def cmd_get_size(self):
        return self.getsize()

    def cmd_toggle_floating(self):
        self.togglefloating()

    def cmd_disable_floating(self):
        self.disablefloating()

    def cmd_enable_floating(self):
        self.enablefloating()

    def cmd_bring_to_front(self):
        if self.floating:
            self.window.configure(stackmode=StackMode.Above)
        else:
            self._reconfigure_floating() #atomatically above

    def cmd_match(self, *args, **kwargs):
        return self.match(*args, **kwargs)

    def cmd_opacity(self, opacity):
        self.opacity = opacity
