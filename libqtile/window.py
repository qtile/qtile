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
import array
import contextlib
import inspect
import traceback

import xcffib.xproto
from xcffib.xproto import EventMask, SetMode, StackMode

from libqtile import hook, utils
from libqtile.command.base import CommandError, CommandObject
from libqtile.log_utils import logger

# ICCM Constants
NoValue = 0x0000
XValue = 0x0001
YValue = 0x0002
WidthValue = 0x0004
HeightValue = 0x0008
AllValues = 0x000F
XNegative = 0x0010
YNegative = 0x0020
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

_NET_WM_STATE_REMOVE = 0
_NET_WM_STATE_ADD = 1
_NET_WM_STATE_TOGGLE = 2


def _geometry_getter(attr):
    def get_attr(self):
        if getattr(self, "_" + attr) is None:
            g = self.window.get_geometry()
            # trigger the geometry setter on all these
            self.x = g.x
            self.y = g.y
            self.width = g.width
            self.height = g.height
        return getattr(self, "_" + attr)
    return get_attr


def _geometry_setter(attr):
    def f(self, value):
        if not isinstance(value, int):
            frame = inspect.currentframe()
            stack_trace = traceback.format_stack(frame)
            logger.error("!!!! setting %s to a non-int %s; please report this!", attr, value)
            logger.error(''.join(stack_trace[:-1]))
            value = int(value)
        setattr(self, "_" + attr, value)
    return f


def _float_getter(attr):
    def getter(self):
        if self._float_info[attr] is not None:
            return self._float_info[attr]

        # we don't care so much about width or height, if not set, default to the window width/height
        if attr in ('width', 'height'):
            return getattr(self, attr)

        raise AttributeError("Floating not yet configured yet")
    return getter


def _float_setter(attr):
    def setter(self, value):
        self._float_info[attr] = value
    return setter


class _Window(CommandObject):
    _window_mask = 0  # override in child class

    def __init__(self, window, qtile):
        self.window, self.qtile = window, qtile
        self.hidden = True
        self.group = None
        self.icons = {}
        window.set_attribute(eventmask=self._window_mask)

        self._float_info = {
            'x': None,
            'y': None,
            'width': None,
            'height': None,
        }
        try:
            g = self.window.get_geometry()
            self._x = g.x
            self._y = g.y
            self._width = g.width
            self._height = g.height
            self._float_info['width'] = g.width
            self._float_info['height'] = g.height
        except xcffib.xproto.DrawableError:
            # Whoops, we were too early, so let's ignore it for now and get the
            # values on demand.
            self._x = None
            self._y = None
            self._width = None
            self._height = None

        self.borderwidth = 0
        self.bordercolor = None
        self.name = "<no name>"
        self.strut = None
        self.state = NormalState
        self._float_state = NOT_FLOATING
        self._demands_attention = False

        self.hints = {
            'input': True,
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
        self.update_hints()

    x = property(fset=_geometry_setter("x"), fget=_geometry_getter("x"))
    y = property(fset=_geometry_setter("y"), fget=_geometry_getter("y"))
    width = property(
        fset=_geometry_setter("width"),
        fget=_geometry_getter("width"),
    )
    height = property(
        fset=_geometry_setter("height"),
        fget=_geometry_getter("height"),
    )

    float_x = property(
        fset=_float_setter("x"),
        fget=_float_getter("x")
    )
    float_y = property(
        fset=_float_setter("y"),
        fget=_float_getter("y")
    )
    float_width = property(
        fset=_float_setter("width"),
        fget=_float_getter("width")
    )
    float_height = property(
        fset=_float_setter("height"),
        fget=_float_getter("height")
    )

    @property
    def has_focus(self):
        return self == self.qtile.current_window

    def has_fixed_size(self):
        try:
            if ('PMinSize' in self.hints['flags'] and
                    'PMaxSize' in self.hints['flags'] and
                    0 < self.hints["min_width"] == self.hints["max_width"] and
                    0 < self.hints["min_height"] == self.hints["max_height"]):
                return True
        except KeyError:
            pass
        return False

    def has_user_set_position(self):
        try:
            if 'USPosition' in self.hints['flags'] or 'PPosition' in self.hints['flags']:
                return True
        except KeyError:
            pass
        return False

    def update_name(self):
        try:
            self.name = self.window.get_name()
        except (xcffib.xproto.WindowError, xcffib.xproto.AccessError):
            return
        hook.fire('client_name_updated', self)

    def update_hints(self):
        """Update the local copy of the window's WM_HINTS

        See http://tronche.com/gui/x/icccm/sec-4.html#WM_HINTS
        """
        try:
            h = self.window.get_wm_hints()
            normh = self.window.get_wm_normal_hints()
        except (xcffib.xproto.WindowError, xcffib.xproto.AccessError):
            return

        if normh:
            self.hints.update(normh)

        if h and 'UrgencyHint' in h['flags']:
            if self.qtile.current_window != self:
                self.hints['urgent'] = True
                hook.fire('client_urgent_hint_changed', self)
        elif self.urgent:
            self.hints['urgent'] = False
            hook.fire('client_urgent_hint_changed', self)

        if h and 'InputHint' in h['flags']:
            self.hints['input'] = h['input']

        if getattr(self, 'group', None):
            self.group.layout_all()

        return

    def update_state(self):
        triggered = ['urgent']

        if self.qtile.config.auto_fullscreen:
            triggered.append('fullscreen')

        state = self.window.get_net_wm_state()

        logger.debug('_NET_WM_STATE: %s', state)
        for s in triggered:
            setattr(self, s, (s in state))

    @property
    def urgent(self):
        return self.hints['urgent'] or self._demands_attention

    @urgent.setter
    def urgent(self, val):
        self._demands_attention = val
        # TODO unset window hint as well?
        if not val:
            self.hints['urgent'] = False

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

    def set_opacity(self, opacity):
        if 0.0 <= opacity <= 1.0:
            real_opacity = int(opacity * 0xffffffff)
            self.window.set_property('_NET_WM_WINDOW_OPACITY', real_opacity)
        else:
            return

    def get_opacity(self):
        opacity = self.window.get_property(
            "_NET_WM_WINDOW_OPACITY", unpack=int
        )
        if not opacity:
            return 1.0
        else:
            value = opacity[0]
            # 2 decimal places
            as_float = round(value / 0xffffffff, 2)
            return as_float

    opacity = property(get_opacity, set_opacity)

    def kill(self):
        if "WM_DELETE_WINDOW" in self.window.get_wm_protocols():
            data = [
                self.qtile.conn.atoms["WM_DELETE_WINDOW"],
                xcffib.xproto.Time.CurrentTime,
                0,
                0,
                0
            ]

            u = xcffib.xproto.ClientMessageData.synthetic(data, "I" * 5)

            e = xcffib.xproto.ClientMessageEvent.synthetic(
                format=32,
                window=self.window.wid,
                type=self.qtile.conn.atoms["WM_PROTOCOLS"],
                data=u
            )

            self.window.send_event(e)
        else:
            self.window.kill_client()
        self.qtile.conn.flush()

    def hide(self):
        # We don't want to get the UnmapNotify for this unmap
        with self.disable_mask(xcffib.xproto.EventMask.StructureNotify):
            self.window.unmap()
        self.state = IconicState
        self.hidden = True

    def unhide(self):
        self.window.map()
        self.state = NormalState
        self.hidden = False

    @contextlib.contextmanager
    def disable_mask(self, mask):
        self._disable_mask(mask)
        yield
        self._reset_mask()

    def _disable_mask(self, mask):
        self.window.set_attribute(
            eventmask=self._window_mask & (~mask)
        )

    def _reset_mask(self):
        self.window.set_attribute(
            eventmask=self._window_mask
        )

    def place(self, x, y, width, height, borderwidth, bordercolor,
              above=False, margin=None):
        """
        Places the window at the specified location with the given size.

        Parameters
        ==========
        x : int
        y : int
        width : int
        height : int
        borderwidth : int
        bordercolor : string
        above : bool, optional
        margin : int or list, optional
            space around window as int or list of ints [N E S W]
        """

        # TODO: self.x/y/height/width are updated BEFORE
        # place is called, so there's no way to know if only
        # the position is changed, so we are sending
        # the ConfigureNotify every time place is called
        #
        # # if position change and size don't
        # # send a configure notify. See ICCCM 4.2.3
        # send_notify = False
        # if (self.x != x or self.y != y) and \
        #    (self.width == width and self.height == height):
        #       send_notify = True
        # #for now, we just:
        send_notify = True

        # Adjust the placement to account for layout margins, if there are any.
        if margin is not None:
            if isinstance(margin, int):
                margin = [margin] * 4
            x += margin[3]
            y += margin[0]
            width -= margin[1] + margin[3]
            height -= margin[0] + margin[2]

        # save x and y float offset
        if self.group is not None and self.group.screen is not None:
            self.float_x = x - self.group.screen.x
            self.float_y = y - self.group.screen.y

        self.x = x
        self.y = y
        self.width = width
        self.height = height

        kwarg = dict(
            x=x,
            y=y,
            width=width,
            height=height,
        )
        if above:
            kwarg['stackmode'] = StackMode.Above

        self.window.configure(**kwarg)
        self.paint_borders(bordercolor, borderwidth)

        if send_notify:
            self.send_configure_notify(x, y, width, height)

    def paint_borders(self, borderpixel, borderwidth):
        self.borderwidth = borderwidth
        self.bordercolor = borderpixel
        self.window.configure(borderwidth=borderwidth)
        self.window.paint_borders(borderpixel)

    def send_configure_notify(self, x, y, width, height):
        """Send a synthetic ConfigureNotify"""

        window = self.window.wid
        above_sibling = False
        override_redirect = False

        event = xcffib.xproto.ConfigureNotifyEvent.synthetic(
            event=window,
            window=window,
            above_sibling=above_sibling,
            x=x,
            y=y,
            width=width,
            height=height,
            border_width=self.borderwidth,
            override_redirect=override_redirect
        )

        self.window.send_event(event, mask=EventMask.StructureNotify)

    def can_steal_focus(self):
        return self.window.get_wm_type() != 'notification'

    def _do_focus(self):
        """
        Focus the window if we can, and return whether or not it was successful.
        """

        # don't focus hidden windows, they should be mapped. this is generally
        # a bug somewhere in the qtile code, but some of the tests do it, so we
        # just have to let it slide for now.
        if self.hidden:
            return False

        # if the window can be focused, just focus it.
        if self.hints['input']:
            self.window.set_input_focus()
            return True

        # does the window want us to ask it about focus?
        if "WM_TAKE_FOCUS" in self.window.get_wm_protocols():
            data = [
                self.qtile.conn.atoms["WM_TAKE_FOCUS"],
                # The timestamp here must be a valid timestamp, not CurrentTime.
                #
                # see https://tronche.com/gui/x/icccm/sec-4.html#s-4.1.7
                # > Windows with the atom WM_TAKE_FOCUS in their WM_PROTOCOLS
                # > property may receive a ClientMessage event from the
                # > window manager (as described in section 4.2.8) with
                # > WM_TAKE_FOCUS in its data[0] field and a valid timestamp
                # > (i.e. not *CurrentTime* ) in its data[1] field.
                self.qtile.core.get_valid_timestamp(),
                0,
                0,
                0
            ]

            u = xcffib.xproto.ClientMessageData.synthetic(data, "I" * 5)
            e = xcffib.xproto.ClientMessageEvent.synthetic(
                format=32,
                window=self.window.wid,
                type=self.qtile.conn.atoms["WM_PROTOCOLS"],
                data=u
            )

            self.window.send_event(e)

        # we didn't focus this time. but now the window knows if it wants
        # focus, it should SetFocus() itself; we'll get another notification
        # about this.
        return False

    def focus(self, warp):
        did_focus = self._do_focus()
        if not did_focus:
            return False

        # now, do all the other WM stuff since the focus actually changed
        if warp and self.qtile.config.cursor_warp:
            self.window.warp_pointer(self.width // 2, self.height // 2)

        if self.urgent:
            self.urgent = False

            atom = self.qtile.conn.atoms["_NET_WM_STATE_DEMANDS_ATTENTION"]
            state = list(self.window.get_property('_NET_WM_STATE', 'ATOM', unpack=int))

            if atom in state:
                state.remove(atom)
                self.window.set_property('_NET_WM_STATE', state)

        self.qtile.root.set_property("_NET_ACTIVE_WINDOW", self.window.wid)
        hook.fire("client_focus", self)
        return True

    def _items(self, name):
        return None

    def _select(self, name, sel):
        return None

    def cmd_focus(self, warp=None):
        """Focuses the window."""
        if warp is None:
            warp = self.qtile.config.cursor_warp
        self.focus(warp=warp)

    def cmd_info(self):
        """Returns a dictionary of info for this object"""
        return self.info()

    def cmd_hints(self):
        """Returns the X11 hints (WM_HINTS and WM_SIZE_HINTS) for this window."""
        return self.hints

    def cmd_inspect(self):
        """Tells you more than you ever wanted to know about a window"""
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
            # "colormap": a.colormap,
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
    """An internal window, that should not be managed by qtile"""
    _window_mask = EventMask.StructureNotify | \
        EventMask.PropertyChange | \
        EventMask.EnterWindow | \
        EventMask.LeaveWindow | \
        EventMask.PointerMotion | \
        EventMask.FocusChange | \
        EventMask.Exposure | \
        EventMask.ButtonPress | \
        EventMask.ButtonRelease | \
        EventMask.KeyPress

    @classmethod
    def create(cls, qtile, x, y, width, height, opacity=1.0):
        win = qtile.conn.create_window(x, y, width, height)
        win.set_property("QTILE_INTERNAL", 1)
        i = Internal(win, qtile)
        i.place(x, y, width, height, 0, None)
        i.opacity = opacity
        return i

    def __repr__(self):
        return "Internal(%r, %s)" % (self.name, self.window.wid)

    def kill(self):
        self.qtile.conn.conn.core.DestroyWindow(self.window.wid)

    def cmd_kill(self):
        self.kill()


class Static(_Window):
    """An internal window, that should not be managed by qtile"""
    _window_mask = EventMask.StructureNotify | \
        EventMask.PropertyChange | \
        EventMask.EnterWindow | \
        EventMask.FocusChange | \
        EventMask.Exposure

    def __init__(self, win, qtile, screen,
                 x=None, y=None, width=None, height=None):
        _Window.__init__(self, win, qtile)
        self.update_name()
        self.conf_x = x
        self.conf_y = y
        self.conf_width = width
        self.conf_height = height
        x = x or 0
        y = y or 0
        self.x = x + screen.x
        self.y = y + screen.y
        self.width = width or 0
        self.height = height or 0
        self.screen = screen
        self.place(self.x, self.y, self.width, self.height, 0, 0)
        self.update_strut()

    def handle_ConfigureRequest(self, e):  # noqa: N802
        cw = xcffib.xproto.ConfigWindow
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

    def update_strut(self):
        strut = self.window.get_property(
            "_NET_WM_STRUT_PARTIAL",
            unpack=int
        )
        strut = strut or self.window.get_property(
            "_NET_WM_STRUT",
            unpack=int
        )
        if strut:
            self.qtile.add_strut(strut)
        self.strut = strut

    def handle_PropertyNotify(self, e):  # noqa: N802
        name = self.qtile.conn.atoms.get_name(e.atom)
        if name in ("_NET_WM_STRUT_PARTIAL", "_NET_WM_STRUT"):
            self.update_strut()

    def __repr__(self):
        return "Static(%r)" % self.name


class Window(_Window):
    _window_mask = EventMask.StructureNotify | \
        EventMask.PropertyChange | \
        EventMask.EnterWindow | \
        EventMask.FocusChange
    # Set when this object is being retired.
    defunct = False

    def __init__(self, window, qtile):
        _Window.__init__(self, window, qtile)
        self._group = None
        self.update_name()
        # add to group by position according to _NET_WM_DESKTOP property
        group = None
        index = window.get_wm_desktop()
        if index is not None and index < len(qtile.groups):
            group = qtile.groups[index]
        elif index is None:
            transient_for = window.get_wm_transient_for()
            win = qtile.windows_map.get(transient_for)
            if win is not None:
                group = win._group
        if group is not None:
            group.add(self)
            self._group = group
            if group != qtile.current_screen.group:
                self.hide()

        # add window to the save-set, so it gets mapped when qtile dies
        qtile.conn.conn.core.ChangeSaveSet(SetMode.Insert, self.window.wid)
        self.update_wm_net_icon()

    @property
    def group(self):
        return self._group

    @group.setter
    def group(self, group):
        if group:
            try:
                self.window.set_property(
                    "_NET_WM_DESKTOP",
                    self.qtile.groups.index(group)
                )
            except xcffib.xproto.WindowError:
                logger.exception("whoops, got error setting _NET_WM_DESKTOP, too early?")
        self._group = group

    @property
    def edges(self):
        return (self.x, self.y, self.x + self.width, self.y + self.height)

    @property
    def floating(self):
        return self._float_state != NOT_FLOATING

    @floating.setter
    def floating(self, do_float):
        if do_float and self._float_state == NOT_FLOATING:
            if self.group and self.group.screen:
                screen = self.group.screen
                self._enablefloating(
                    screen.x + self.float_x, screen.y + self.float_y, self.float_width, self.float_height
                )
            else:
                # if we are setting floating early, e.g. from a hook, we don't have a screen yet
                self._float_state = FLOATING
        elif (not do_float) and self._float_state != NOT_FLOATING:
            if self._float_state == FLOATING:
                # store last size
                self.float_width = self.width
                self.float_height = self.height
            self._float_state = NOT_FLOATING
            self.group.mark_floating(self, False)
            hook.fire('float_change')

    def toggle_floating(self):
        self.floating = not self.floating

    @property
    def fullscreen(self):
        return self._float_state == FULLSCREEN

    @fullscreen.setter
    def fullscreen(self, do_full):
        atom = set([self.qtile.conn.atoms["_NET_WM_STATE_FULLSCREEN"]])
        prev_state = set(self.window.get_property('_NET_WM_STATE', 'ATOM', unpack=int))

        def set_state(old_state, new_state):
            if new_state != old_state:
                self.window.set_property('_NET_WM_STATE', list(new_state))

        if do_full:
            screen = self.group.screen or \
                self.qtile.find_closest_screen(self.x, self.y)

            self._enablefloating(
                screen.x,
                screen.y,
                screen.width,
                screen.height,
                new_float_state=FULLSCREEN
            )
            set_state(prev_state, prev_state | atom)
            return

        if self._float_state == FULLSCREEN:
            # The order of calling set_state() and then
            # setting self.floating = False is important
            set_state(prev_state, prev_state - atom)
            self.floating = False
            return

    def toggle_fullscreen(self):
        self.fullscreen = not self.fullscreen

    @property
    def maximized(self):
        return self._float_state == MAXIMIZED

    @maximized.setter
    def maximized(self, do_maximize):
        if do_maximize:
            screen = self.group.screen or \
                self.qtile.find_closest_screen(self.x, self.y)

            self._enablefloating(
                screen.dx,
                screen.dy,
                screen.dwidth,
                screen.dheight,
                new_float_state=MAXIMIZED
            )
        else:
            if self._float_state == MAXIMIZED:
                self.floating = False

    def toggle_maximize(self, state=MAXIMIZED):
        self.maximized = not self.maximized

    @property
    def minimized(self):
        return self._float_state == MINIMIZED

    @minimized.setter
    def minimized(self, do_minimize):
        if do_minimize:
            if self._float_state != MINIMIZED:
                self._enablefloating(new_float_state=MINIMIZED)
        else:
            if self._float_state == MINIMIZED:
                self.floating = False

    def toggle_minimize(self):
        self.minimized = not self.minimized

    def cmd_static(self, screen=None, x=None, y=None, width=None, height=None):
        """Makes this window a static window, attached to a Screen

        If any of the arguments are left unspecified, the values given by the
        window itself are used instead. So, for a window that's aware of its
        appropriate size and location (like dzen), you don't have to specify
        anything.
        """
        self.defunct = True
        if screen is None:
            screen = self.qtile.current_screen
        else:
            screen = self.qtile.screens[screen]
        if self.group:
            self.group.remove(self)
        s = Static(self.window, self.qtile, screen, x, y, width, height)
        self.qtile.windows_map[self.window.wid] = s
        hook.fire("client_managed", s)

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

        screen = self.qtile.find_closest_screen(
            self.x + self.width // 2, self.y + self.height // 2
        )
        if self.group and screen is not None and screen != self.group.screen:
            self.group.remove(self, force=True)
            screen.group.add(self, force=True)
            self.qtile.focus_screen(screen.index)

        self._reconfigure_floating()

    def getsize(self):
        return (self.width, self.height)

    def getposition(self):
        return (self.x, self.y)

    def _reconfigure_floating(self, new_float_state=FLOATING):
        if new_float_state == MINIMIZED:
            self.hide()
        else:
            width = self.width
            height = self.height

            flags = self.hints.get("flags", {})
            if "PMinSize" in flags:
                width = max(self.width, self.hints.get('min_width', 0))
                height = max(self.height, self.hints.get('min_height', 0))
            if "PMaxSize" in flags:
                width = min(width, self.hints.get('max_width', 0)) or width
                height = min(height, self.hints.get('max_height', 0)) or height

            if self.hints['base_width'] and self.hints['width_inc']:
                width_adjustment = (width - self.hints['base_width']) % self.hints['width_inc']
                width -= width_adjustment
                if new_float_state == FULLSCREEN:
                    self.x += int(width_adjustment / 2)

            if self.hints['base_height'] and self.hints['height_inc']:
                height_adjustment = (height - self.hints['base_height']) % self.hints['height_inc']
                height -= height_adjustment
                if new_float_state == FULLSCREEN:
                    self.y += int(height_adjustment / 2)

            self.place(
                self.x, self.y,
                width, height,
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

    def togroup(self, group_name=None, *, switch_group=False):
        """Move window to a specified group

        Also switch to that group if switch_group is True.
        """
        if group_name is None:
            group = self.qtile.current_group
        else:
            group = self.qtile.groups_map.get(group_name)
            if group is None:
                raise CommandError("No such group: %s" % group_name)

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
            if switch_group:
                group.cmd_toscreen(toggle=False)

    def toscreen(self, index=None):
        """Move window to a specified screen, or the current screen."""
        if index is None:
            screen = self.qtile.current_screen
        else:
            try:
                screen = self.qtile.screens[index]
            except IndexError:
                raise CommandError('No such screen: %d' % index)
        self.togroup(screen.group.name)

    def match(self, match):
        """Match window against given attributes.

        Parameters
        ==========
        match:
            a config.Match object
        """
        try:
            return match.compare(self)
        except (xcffib.xproto.WindowError, xcffib.xproto.AccessError):
            return False

    def handle_EnterNotify(self, e):  # noqa: N802
        hook.fire("client_mouse_enter", self)
        if self.qtile.config.follow_mouse_focus:
            if self.group.current_window != self:
                self.group.focus(self, False)
            if self.group.screen and self.qtile.current_screen != self.group.screen:
                self.qtile.focus_screen(self.group.screen.index, False)
        return True

    def handle_ConfigureRequest(self, e):  # noqa: N802
        if self.qtile._drag and self.qtile.current_window == self:
            # ignore requests while user is dragging window
            return
        if getattr(self, 'floating', False):
            # only obey resize for floating windows
            cw = xcffib.xproto.ConfigWindow
            width = e.width if e.value_mask & cw.Width else self.width
            height = e.height if e.value_mask & cw.Height else self.height
            x = e.x if e.value_mask & cw.X else self.x
            y = e.y if e.value_mask & cw.Y else self.y
        else:
            width, height, x, y = self.width, self.height, self.x, self.y

        if self.group and self.group.screen:
            self.place(
                x, y,
                width, height,
                self.borderwidth, self.bordercolor,
            )
        self.update_state()
        return False

    def update_wm_net_icon(self):
        """Set a dict with the icons of the window"""

        icon = self.window.get_property('_NET_WM_ICON', 'CARDINAL')
        if not icon:
            return
        icon = list(map(ord, icon.value))

        icons = {}
        while True:
            if not icon:
                break
            size = icon[:8]
            if len(size) != 8 or not size[0] or not size[4]:
                break

            icon = icon[8:]

            width = size[0]
            height = size[4]

            next_pix = width * height * 4
            data = icon[:next_pix]

            arr = array.array("B", data)
            for i in range(0, len(arr), 4):
                mult = arr[i + 3] / 255.
                arr[i + 0] = int(arr[i + 0] * mult)
                arr[i + 1] = int(arr[i + 1] * mult)
                arr[i + 2] = int(arr[i + 2] * mult)
            icon = icon[next_pix:]
            icons["%sx%s" % (width, height)] = arr
        self.icons = icons
        hook.fire("net_wm_icon_change", self)

    def handle_ClientMessage(self, event):  # noqa: N802
        atoms = self.qtile.conn.atoms

        opcode = event.type
        data = event.data
        if atoms["_NET_WM_STATE"] == opcode:
            prev_state = self.window.get_property(
                '_NET_WM_STATE',
                'ATOM',
                unpack=int
            )

            current_state = set(prev_state)

            action = data.data32[0]
            for prop in (data.data32[1], data.data32[2]):
                if not prop:
                    # skip 0
                    continue

                if action == _NET_WM_STATE_REMOVE:
                    current_state.discard(prop)
                elif action == _NET_WM_STATE_ADD:
                    current_state.add(prop)
                elif action == _NET_WM_STATE_TOGGLE:
                    current_state ^= set([prop])  # toggle :D

            self.window.set_property('_NET_WM_STATE', list(current_state))
        elif atoms["_NET_ACTIVE_WINDOW"] == opcode:
            source = data.data32[0]
            if source == 2:  # XCB_EWMH_CLIENT_SOURCE_TYPE_NORMAL
                logger.info("Focusing window by pager")
                self.qtile.current_screen.set_group(self.group)
                self.group.focus(self)
            else:  # XCB_EWMH_CLIENT_SOURCE_TYPE_OTHER
                focus_behavior = self.qtile.config.focus_on_window_activation
                if focus_behavior == "focus":
                    logger.info("Focusing window")
                    self.qtile.current_screen.set_group(self.group)
                    self.group.focus(self)
                elif focus_behavior == "smart" and self.group.screen and self.group.screen == self.qtile.current_screen:
                    logger.info("Focusing window")
                    self.qtile.current_screen.set_group(self.group)
                    self.group.focus(self)
                elif focus_behavior == "urgent" or (focus_behavior == "smart" and not self.group.screen):
                    logger.info("Setting urgent flag for window")
                    self.urgent = True
                elif focus_behavior == "never":
                    logger.info("Ignoring focus request")
                else:
                    logger.warning("Invalid value for focus_on_window_activation: {}".format(focus_behavior))
        elif atoms["_NET_CLOSE_WINDOW"] == opcode:
            self.kill()
        elif atoms["WM_CHANGE_STATE"] == opcode:
            state = data.data32[0]
            if state == NormalState:
                self.minimized = False
            elif state == IconicState:
                self.minimized = True
        else:
            logger.info("Unhandled client message: %s", atoms.get_name(opcode))

    def handle_PropertyNotify(self, e):  # noqa: N802
        name = self.qtile.conn.atoms.get_name(e.atom)
        logger.debug("PropertyNotifyEvent: %s", name)
        if name == "WM_TRANSIENT_FOR":
            pass
        elif name == "WM_HINTS":
            self.update_hints()
        elif name == "WM_NORMAL_HINTS":
            self.update_hints()
        elif name == "WM_NAME":
            self.update_name()
        elif name == "_NET_WM_NAME":
            self.update_name()
        elif name == "_NET_WM_VISIBLE_NAME":
            self.update_name()
        elif name == "WM_ICON_NAME":
            pass
        elif name == "_NET_WM_ICON_NAME":
            pass
        elif name == "_NET_WM_ICON":
            self.update_wm_net_icon()
        elif name == "ZOOM":
            pass
        elif name == "_NET_WM_WINDOW_OPACITY":
            pass
        elif name == "WM_STATE":
            pass
        elif name == "_NET_WM_STATE":
            self.update_state()
        elif name == "WM_PROTOCOLS":
            pass
        elif name == "_NET_WM_DESKTOP":
            # Some windows set the state(fullscreen) when starts,
            # update_state is here because the group and the screen
            # are set when the property is emitted
            # self.update_state()
            self.update_state()
        elif name == "_NET_WM_USER_TIME":
            if not self.qtile.config.follow_mouse_focus and \
                    self.group.current_window != self:
                self.group.focus(self, False)
        else:
            logger.info("Unknown window property: %s", name)
        return False

    def _items(self, name):
        if name == "group":
            return (True, None)
        elif name == "layout":
            return (True, list(range(len(self.group.layouts))))
        elif name == "screen":
            return (True, None)

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
        return "Window(%r)" % self.name

    def cmd_kill(self):
        """Kill this window

        Try to do this politely if the client support
        this, otherwise be brutal.
        """
        self.kill()

    def cmd_togroup(self, groupName=None, *, switch_group=False):  # noqa: 803
        """Move window to a specified group.

        If groupName is not specified, we assume the current group.
        If switch_group is True, also switch to that group.

        Examples
        ========

        Move window to current group::

            togroup()

        Move window to group "a"::

            togroup("a")

        Move window to group "a", and switch to group "a"::

            togroup("a", switch_group=True)
        """
        self.togroup(groupName, switch_group=switch_group)

    def cmd_toscreen(self, index=None):
        """Move window to a specified screen.

        If index is not specified, we assume the current screen

        Examples
        ========

        Move window to current screen::

            toscreen()

        Move window to screen 0::

            toscreen(0)
        """
        self.toscreen(index)

    def cmd_move_floating(self, dx, dy):
        """Move window by dx and dy"""
        self.tweak_float(dx=dx, dy=dy)

    def cmd_resize_floating(self, dw, dh):
        """Add dw and dh to size of window"""
        self.tweak_float(dw=dw, dh=dh)

    def cmd_set_position_floating(self, x, y):
        """Move window to x and y"""
        self.tweak_float(x=x, y=y)

    def cmd_set_size_floating(self, w, h):
        """Set window dimensions to w and h"""
        self.tweak_float(w=w, h=h)

    def cmd_place(self, x, y, width, height, borderwidth, bordercolor,
                  above=False, margin=None):
        self.place(x, y, width, height, borderwidth, bordercolor, above,
                   margin)

    def cmd_get_position(self):
        return self.getposition()

    def cmd_get_size(self):
        return self.getsize()

    def cmd_toggle_floating(self):
        self.toggle_floating()

    def cmd_enable_floating(self):
        self.floating = True

    def cmd_disable_floating(self):
        self.floating = False

    def cmd_toggle_maximize(self):
        self.toggle_maximize()

    def cmd_toggle_fullscreen(self):
        self.toggle_fullscreen()

    def cmd_enable_fullscreen(self):
        self.fullscreen = True

    def cmd_disable_fullscreen(self):
        self.fullscreen = False

    def cmd_toggle_minimize(self):
        self.toggle_minimize()

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

    def _is_in_window(self, x, y, window):
        return (window.edges[0] <= x <= window.edges[2] and
                window.edges[1] <= y <= window.edges[3])

    def cmd_set_position(self, x, y):
        if self.floating:
            self.tweak_float(x, y)
            return
        for window in self.group.windows:
            if window == self or window.floating:
                continue
            curx, cury = self.qtile.get_mouse_position()
            if self._is_in_window(curx, cury, window):
                clients = self.group.layout.clients
                index1 = clients.index(self)
                index2 = clients.index(window)
                clients[index1], clients[index2] = clients[index2], clients[index1]
                self.group.layout.focused = index2
                self.group.layout_all()
                break
