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

import struct
import contextlib
import xcb.xcb
from xcb.xproto import EventMask, StackMode, SetMode
import xcb.xproto
import command
import utils
import hook


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
PAllHints = (PPosition | PSize | PMinSize | PMaxSize | PResizeInc | PAspect)
InputHint = (1 << 0)
StateHint = (1 << 1)
IconPixmapHint = (1 << 2)
IconWindowHint = (1 << 3)
IconPositionHint = (1 << 4)
IconMaskHint = (1 << 5)
WindowGroupHint = (1 << 6)
MessageHint = (1 << 7)
UrgencyHint = (1 << 8)
AllHints = (InputHint | StateHint | IconPixmapHint | IconWindowHint |
            IconPositionHint | IconMaskHint | WindowGroupHint | MessageHint |
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

# float states
NOT_FLOATING = 1  # not floating
FLOATING = 2
MAXIMIZED = 3
FULLSCREEN = 4
TOP = 5
MINIMIZED = 6


class _Window(command.CommandObject):
    def __init__(self, window, qtile):
        self.window, self.qtile = window, qtile
        self.hidden = True
        self.group = None
        window.set_attribute(eventmask=self._windowMask)
        try:
            g = self.window.get_geometry()
            self._x, self._y, self._width, self._height = g.x, g.y, g.width, g.height
            # note that _float_info x and y are
            # really offsets, relative to screen x,y
            self._float_info = {
                'x': g.x,
                'y': g.y,
                'w': g.width,
                'h': g.height,
            }
        except xcb.xproto.BadDrawable:
            # Whoops, we were too early, so let's ignore it for now and get the
            # values on demand.
            self._x, self._y, self._width, self._height = None, None, None, None
            self._float_info = None
        self.borderwidth = 0
        self.bordercolor = None
        self.name = "<no name>"
        self.state = NormalState
        self.window_type = "normal"
        self._float_state = NOT_FLOATING

        self.hints = {
            'input': True,
            'state': NormalState,  # Normal state
            'icon_pixmap': None,
            'icon_window': None,
            'icon_x': 0,
            'icon_y': 0,
            'icon_mask': 0,
            'window_group': None,
            'urgent': False,
            # normal or size hints
            'width_inc': None,
            'height_inc': None,
            'base_width': 0,
            'base_height': 0,
            }
        self.updateHints()

    def _geometry_getter(attr):
        def get_attr(self):
            if getattr(self, "_" + attr) is None:
                g = self.window.get_geometry()
                self._x, self._y = g.x, g.y
                self._width, self._height = g.width, g.height
                # note that _float_info x and y are
                # really offsets, relative to screen x,y
                self._float_info = {
                    'x': g.x, 'y': g.y,
                    'w': g.width, 'h': g.height
                }

            return getattr(self, "_" + attr)
        return get_attr

    def _geometry_setter(attr):
        return lambda self, value: setattr(self, "_" + attr, value)

    x = property(fset=_geometry_setter("x"), fget=_geometry_getter("x"))
    y = property(fset=_geometry_setter("y"), fget=_geometry_getter("y"))
    width = property(
        fset=_geometry_setter("width"),
        fget=_geometry_getter("width"))
    height = property(
        fset=_geometry_setter("height"),
        fget=_geometry_getter("height"))
    _float_info = property(
        fset=_geometry_setter("_float_info"),
        fget=_geometry_getter("_float_info"))

    def updateName(self):
        try:
            self.name = self.window.get_name()
        except (xcb.xproto.BadWindow, xcb.xproto.BadAccess):
            return
        hook.fire("window_name_change")

    def updateHints(self):
        """
            update the local copy of the window's WM_HINTS
            http://tronche.com/gui/x/icccm/sec-4.html#WM_HINTS
        """
        try:
            h = self.window.get_wm_hints()
            normh = self.window.get_wm_normal_hints()
        except (xcb.xproto.BadWindow, xcb.xproto.BadAccess):
            return

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

        if normh:
            normh.pop('flags')
            if(not normh['base_width']
                and normh['min_width'] and normh['width_inc']):
                # seems xcb does ignore base width :(
                normh['base_width'] = (normh['min_width'] %
                                       normh['width_inc'])
            if(not normh['base_height']
                and normh['min_height'] and normh['height_inc']):
                # seems xcb does ignore base height :(
                normh['base_height'] = (normh['min_height'] %
                                        normh['height_inc'])
            self.hints.update(normh)

        if h and 'UrgencyHint' in h['flags']:
            self.hints['urgent'] = True
            hook.fire('client_urgent_hint_changed', self)
        elif self.urgent:
            self.hints['urgent'] = False
            hook.fire('client_urgent_hint_changed', self)

        if getattr(self, 'group', None):
            self.group.layoutAll()

        return

    def updateState(self):
        self.fullscreen = self.window.get_net_wm_state() == 'fullscreen'

    @property
    def urgent(self):
        return self.hints['urgent']

    def info(self):
        if self.group:
            group = self.group.name
        else:
            group = None
        return dict(
            name=self.name,
            x=self.x,
            y=self.y,
            width=self.width,
            height=self.height,
            group=group,
            id=self.window.wid,
            floating=self._float_state != NOT_FLOATING,
            float_info=self._float_info,
            maximized=self._float_state == MAXIMIZED,
            minimized=self._float_state == MINIMIZED,
            fullscreen=self._float_state == FULLSCREEN
        )

    @property
    def state(self):
        return self.window.get_wm_state()[0]

    @state.setter
    def state(self, val):
        if val in (WithdrawnState, NormalState, IconicState):
            self.window.set_property('WM_STATE', [val, 0])

    def setOpacity(self, opacity):
        if 0.0 <= opacity <= 1.0:
            real_opacity = int(opacity * 0xffffffff)
            self.window.set_property('_NET_WM_WINDOW_OPACITY', real_opacity)
        else:
            return

    def getOpacity(self):
        opacity = self.window.get_property(
            "_NET_WM_WINDOW_OPACITY", unpack="I")
        if not opacity:
            return 1.0
        else:
            value = opacity[0]
            as_float = round(
                (float(value) / 0xffffffff),
                2  # 2 decimal places
                )
            return as_float

    opacity = property(getOpacity, setOpacity)

    def kill(self):
        if "WM_DELETE_WINDOW" in self.window.get_wm_protocols():
            #e = event.ClientMessage(
            #        window = self.window,
            #        client_type = self.qtile.display.intern_atom(
            #             "WM_PROTOCOLS"),
            #        data = [
            #            # Use 32-bit format:
            #            32,
            #            # Must be exactly 20 bytes long:
            #            [
            #                self.qtile.display.intern_atom(
            #                        "WM_DELETE_WINDOW"),
            #                X.CurrentTime,
            #                0,
            #                0,
            #                0
            #            ]
            #        ]
            #)
            vals = [
                33,  # ClientMessageEvent
                32,  # Format
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
        self.state = NormalState
        self.hidden = False

    @contextlib.contextmanager
    def disableMask(self, mask):
        self._disableMask(mask)
        yield
        self._resetMask()

    def _disableMask(self, mask):
        self.window.set_attribute(
            eventmask=self._windowMask & (~mask)
        )

    def _resetMask(self):
        self.window.set_attribute(
            eventmask=self._windowMask
        )

    def place(self, x, y, width, height, borderwidth, bordercolor,
        above=False, force=False, twice=False):
        """
            Places the window at the specified location with the given size.

            if force is false, than it tries to obey hints
            if twice is true, that it does positioning twice (useful for some
                gtk apps)
        """
        # TODO(tailhook) uncomment resize increments when we'll decide
        #                to obey all those hints
        #if self.hints['width_inc']:
        #    width = (width -
        #        ((width - self.hints['base_width']) %
        #        self.hints['width_inc']))
        #if self.hints['height_inc']:
        #    height = (height -
        #        ((height - self.hints['base_height'])
        #        % self.hints['height_inc']))
        # TODO(tailhook) implement min-size, maybe
        # TODO(tailhook) implement max-size
        # TODO(tailhook) implement gravity
        self.x, self.y, self.width, self.height = x, y, width, height
        self.borderwidth, self.bordercolor = borderwidth, bordercolor

        # save x and y float offset
        if self.group is not None and self.group.screen is not None:
            self._float_info['x'] = x - self.group.screen.x
            self._float_info['y'] = y - self.group.screen.y

        kwarg = dict(
            x=x,
            y=y,
            width=width,
            height=height,
            borderwidth=borderwidth,
            )
        if above:
            kwarg['stackmode'] = StackMode.Above

        # Oh, yes we do this twice
        #
        # This sort of weird thing is because GTK assumes that each it's
        # configure request is replied with configure notify. But X server
        # is smarter than that and does not send configure notify if size is
        # not changed. So we hack this.
        #
        # And no, manually sending ConfigureNotifyEvent does nothing, really!
        #
        # We use increment position because its more probably will
        # lead to less calculations on the application side (no word
        # rewrapping, widget resizing, etc.)
        #
        # TODO(tailhook) may be configure notify event will work for reparented
        # windows
        if twice:
            kwarg['y'] -= 1
            self.window.configure(**kwarg)
            kwarg['y'] += 1
        self.window.configure(**kwarg)

        if bordercolor is not None:
            self.window.set_attribute(
                borderpixel=bordercolor
            )

    def focus(self, warp):
        if not self.hidden:
            if "WM_TAKE_FOCUS" in self.window.get_wm_protocols():
                vals = [
                    33,
                    32,
                    0,
                    self.window.wid,
                    self.qtile.conn.atoms["WM_PROTOCOLS"],
                    self.qtile.conn.atoms["WM_TAKE_FOCUS"],
                    xcb.xproto.Time.CurrentTime,
                    0,
                    0,
                    0,
                ]
                e = struct.pack('BBHII5I', *vals)
                self.window.send_event(e)
            if self.hints['input']:
                    self.window.set_input_focus()
            try:
                if warp and self.qtile.config.cursor_warp:
                    self.window.warp_pointer(self.width // 2, self.height // 2)
            except AttributeError:
                pass
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
            name=self.window.get_name(),
            wm_class=self.window.get_wm_class(),
            wm_window_role=self.window.get_wm_window_role(),
            wm_type=self.window.get_wm_type(),
            wm_transient_for=self.window.get_wm_transient_for(),
            protocols=protocols,
            wm_icon_name=self.window.get_wm_icon_name(),
            wm_client_machine=self.window.get_wm_client_machine(),
            normalhints=normalhints,
            hints=hints,
            state=state,
            float_info=self._float_info
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
        return "Internal(%s, %s)" % (self.name, self.window.wid)


class Static(_Window):
    """
        An internal window, that should not be managed by qtile.
    """
    _windowMask = EventMask.StructureNotify |\
                  EventMask.PropertyChange |\
                  EventMask.EnterWindow |\
                  EventMask.FocusChange |\
                  EventMask.Exposure

    def __init__(self, win, qtile, screen,
                 x=None, y=None, width=None, height=None):
        _Window.__init__(self, win, qtile)
        self.updateName()
        self.conf_x, self.conf_y = x, y
        self.conf_width, self.conf_height = width, height
        self.x = x or 0
        self.y = y or 0
        self.width = width or 0
        self.height = height or 0
        self.screen = screen
        if None not in (x, y, width, height):
            self.place(x, y, width, height, 0, 0)

    def handle_ConfigureRequest(self, e):
        cw = xcb.xproto.ConfigWindow
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
        return False

    def __repr__(self):
        return "Static(%s)" % self.name


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

        # add window to the save-set, so it gets mapped when qtile dies
        qtile.conn.conn.core.ChangeSaveSet(SetMode.Insert, self.window.wid)

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
        return self._float_state != NOT_FLOATING

    @floating.setter
    def floating(self, do_float):
        if do_float:
            if self._float_state == NOT_FLOATING:
                self.enablefloating()

    @property
    def fullscreen(self):
        return self._float_state == FULLSCREEN

    @fullscreen.setter
    def fullscreen(self, do_full):
        if do_full:
            if self._float_state != FULLSCREEN:
                self.enablemaximize(state=FULLSCREEN)
        else:
            if self._float_state == FULLSCREEN:
                self.disablefloating()

    @property
    def maximized(self):
        return self._float_state == MAXIMIZED

    @maximized.setter
    def maximized(self, do_maximize):
        if do_maximize:
            if self._float_state != MAXIMIZED:
                self.enablemaximize()
        else:
            if self._float_state == MAXIMIZED:
                self.disablefloating()

    @property
    def minimized(self):
        return self._float_state == MINIMIZED

    @minimized.setter
    def minimized(self, do_minimize):
        if do_minimize:
            if self._float_state != MINIMIZED:
                self.enableminimize()
        else:
            if self._float_state == MINIMIZED:
                self.disablefloating()

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

    def tweak_float(self, x=None, y=None, dx=0, dy=0,
                    w=None, h=None, dw=0, dh=0):
        if x is not None:
            self.x = x
        self.x += dx

        if y is not None:
            self.y = y
        self.y += dy

        if w is not None:
            self.width = w
        self.width += dw

        if h is not None:
            self.height = h
        self.height += dh

        if self.height < 0:
            self.height = 0
        if self.width < 0:
            self.width = 0

        screen = self.qtile.find_closest_screen(self.x, self.y)
        if screen is not None and screen != self.group.screen:
            self.group.remove(self)
            screen.group.add(self)
            self.qtile.toScreen(screen.index)
            # TODO - need to kick boxes to update

        self._reconfigure_floating()

    def getsize(self):
        return self.width, self.height

    def getposition(self):
        return self.x, self.y

    def toggleminimize(self):
        if self.minimized:
            self.disablefloating()
        else:
            self.enableminimize()

    def enableminimize(self):
        self._enablefloating(new_float_state=MINIMIZED)

    def togglemaximize(self, state=MAXIMIZED):
        if self._float_state == state:
            self.disablefloating()
        else:
            self.enablemaximize(state)

    def enablemaximize(self, state=MAXIMIZED):
        screen = self.group.screen
        if state == MAXIMIZED:
            self._enablefloating(screen.dx,
                             screen.dy,
                             screen.dwidth,
                             screen.dheight,
                             new_float_state=state)
        elif state == FULLSCREEN:
            self._enablefloating(screen.x,
                                 screen.y,
                                 screen.width,
                                 screen.height,
                                 new_float_state=state)

    def togglefloating(self):
        if self.floating:
            self.disablefloating()
        else:
            self.enablefloating()

    def _reconfigure_floating(self, new_float_state=FLOATING):
        if new_float_state == MINIMIZED:
            self.state = IconicState
            self.hide()
        else:
            # make sure x, y is on the screen
            screen = self.qtile.find_closest_screen(self.x, self.y)
            if (screen is not None and self.group is not None and
                self.group.screen is not None and
                screen != self.group.screen):
                self.x = self.group.screen.x
                self.y = self.group.screen.y

            self.place(self.x,
                   self.y,
                   self.width,
                   self.height,
                   self.borderwidth,
                   self.bordercolor,
                   above=True,
                   )
        if self._float_state != new_float_state:
            self._float_state = new_float_state
            if self.group:  # may be not, if it's called from hook
                self.group.mark_floating(self, True)
            hook.fire('float_change')

    def _enablefloating(self, x=None, y=None, w=None, h=None,
                        new_float_state=FLOATING):
        if new_float_state != MINIMIZED:
            self.x = x
            self.y = y
            self.width = w
            self.height = h
        self._reconfigure_floating(new_float_state=new_float_state)

    def enablefloating(self):
        fi = self._float_info
        self._enablefloating(fi['x'], fi['y'], fi['w'], fi['h'])

    def disablefloating(self):
        if self._float_state != NOT_FLOATING:
            if self._float_state == FLOATING:
                # store last size
                fi = self._float_info
                fi['w'] = self.width
                fi['h'] = self.height
            self._float_state = NOT_FLOATING
            self.group.mark_floating(self, False)
            hook.fire('float_change')

    def togroup(self, groupName):
        """
            Move window to a specified group.
        """
        group = self.qtile.groupMap.get(groupName)
        if group is None:
            raise command.CommandError("No such group: %s" % groupName)

        if self.group is not group:
            self.hide()
            if self.group:
                if self.group.screen:
                    # for floats remove window offset
                    self.x -= self.group.screen.x
                self.group.remove(self)

            if group.screen and self.x < group.screen.x:
                self.x += group.screen.x
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
            raise TypeError(
                "Either a name, a wmclass or a role must be specified")
        if wname and wname == self.name:
            return True

        try:

            cliclass = self.window.get_wm_class()
            if wmclass and cliclass and wmclass in cliclass:
                return True

            clirole = self.window.get_wm_window_role()
            if role and clirole and role == clirole:
                return True

        except (xcb.xproto.BadWindow, xcb.xproto.BadAccess):
            return False

        return False

    def handle_EnterNotify(self, e):
        hook.fire("client_mouse_enter", self)
        if self.qtile.config.follow_mouse_focus and \
                        self.group.currentWindow != self:
            self.group.focus(self, False)
        if self.group.screen and \
            self.qtile.currentScreen != self.group.screen and \
            self.qtile.config.follow_mouse_focus:
            self.qtile.toScreen(self.group.screen.index)
        return True

    def handle_ConfigureRequest(self, e):
        if self.qtile._drag and self.qtile.currentWindow == self:
            # ignore requests while user is dragging window
            return
        if getattr(self, 'floating', False):
            # only obey resize for floating windows
            screen = self.group.screen
            cw = xcb.xproto.ConfigWindow
            if e.value_mask & cw.Width:
                self.width = e.width
            if e.value_mask & cw.Height:
                self.height = e.height
            if e.value_mask & cw.X:
                self.x = screen.x + ((screen.width - self.width) // 2)
            if e.value_mask & cw.Y:
                self.y = screen.y + ((screen.height - self.height) // 2)
        if self.group and self.group.screen:
            self.place(
                self.x,
                self.y,
                self.width,
                self.height,
                self.borderwidth,
                self.bordercolor,
                twice=True,
            )
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
        elif name == "WM_ICON_NAME":
            pass
        elif name == "_NET_WM_ICON_NAME":
            pass
        elif name == "ZOOM":
            pass
        elif name == "_NET_WM_WINDOW_OPACITY":
            pass
        elif name == "WM_STATE":
            pass
        elif name == "_NET_WM_STATE":
            self.updateState()
        elif name == "WM_PROTOCOLS":
            pass
        elif name == "_NET_WM_DESKTOP":
            pass
        elif name == "_NET_WM_USER_TIME":
            if not self.qtile.config.follow_mouse_focus and \
                            self.group.currentWindow != self:
                self.group.focus(self, False)
        else:
            self.qtile.log.info("Unknown window property: %s" % name)
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
        return "Window(%s)" % self.name

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

    def cmd_move_floating(self, dx, dy):
        """
            Move window by dx and dy
        """
        self.tweak_float(dx=dx, dy=dy)

    def cmd_resize_floating(self, dw, dh):
        """
            Add dw and dh to size of window
        """
        self.tweak_float(dw=dw, dh=dh)

    def cmd_set_position_floating(self, x, y):
        """
            Move window to x and y
        """
        self.tweak_float(x=x, y=y)

    def cmd_set_size_floating(self, w, h):
        """
            Set window dimensions to w and h
        """
        self.tweak_float(w=w, h=h)

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

    def cmd_toggle_maximize(self):
        self.togglemaximize()

    def cmd_disable_maximimize(self):
        self.disablefloating()

    def cmd_enable_maximize(self):
        self.enablemaximize()

    def cmd_toggle_fullscreen(self):
        self.togglemaximize(state=FULLSCREEN)

    def cmd_enable_fullscreen(self):
        self.enablemaximize(state=FULLSCREEN)

    def cmd_disable_fullscreen(self):
        self.disablefloating()

    def cmd_toggle_minimize(self):
        self.toggleminimize()

    def cmd_enable_minimize(self):
        self.enableminimize()

    def cmd_disable_minimize(self):
        self.disablefloating()

    def cmd_bring_to_front(self):
        if self.floating:
            self.window.configure(stackmode=StackMode.Above)
        else:
            self._reconfigure_floating()  # atomatically above

    def cmd_match(self, *args, **kwargs):
        return self.match(*args, **kwargs)

    def cmd_opacity(self, opacity):
        if opacity < .1:
            self.opacity = .1
        elif opacity > 1:
            self.opacity = 1
        else:
            self.opacity = opacity

    def cmd_down_opacity(self):
        if self.opacity > .2:
            # don't go completely clear
            self.opacity -= .1
        else:
            self.opacity = .1

    def cmd_up_opacity(self):
        if self.opacity < .9:
            self.opacity += .1
        else:
            self.opacity = 1
