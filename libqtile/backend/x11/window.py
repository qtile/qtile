from __future__ import annotations

import array
import contextlib
import inspect
import traceback
from itertools import islice
from types import FunctionType
from typing import TYPE_CHECKING

import xcffib
import xcffib.xproto
from xcffib.wrappers import GContextID, PixmapID
from xcffib.xproto import EventMask, SetMode

from libqtile import bar, hook, utils
from libqtile.backend import base
from libqtile.backend.base import FloatStates
from libqtile.backend.x11 import xcbq
from libqtile.backend.x11.drawer import Drawer
from libqtile.command.base import CommandError, expose_command
from libqtile.log_utils import logger
from libqtile.scratchpad import ScratchPad

if TYPE_CHECKING:
    from libqtile.command.base import ItemT

# ICCM Constants
NoValue = 0x0000
XValue = 0x0001
YValue = 0x0002
WidthValue = 0x0004
HeightValue = 0x0008
AllValues = 0x000F
XNegative = 0x0010
YNegative = 0x0020
InputHint = 1 << 0
StateHint = 1 << 1
IconPixmapHint = 1 << 2
IconWindowHint = 1 << 3
IconPositionHint = 1 << 4
IconMaskHint = 1 << 5
WindowGroupHint = 1 << 6
MessageHint = 1 << 7
UrgencyHint = 1 << 8
AllHints = (
    InputHint
    | StateHint
    | IconPixmapHint
    | IconWindowHint
    | IconPositionHint
    | IconMaskHint
    | WindowGroupHint
    | MessageHint
    | UrgencyHint
)

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
            self.depth = g.depth
        return getattr(self, "_" + attr)

    return get_attr


def _geometry_setter(attr):
    def f(self, value):
        if not isinstance(value, int):
            frame = inspect.currentframe()
            stack_trace = traceback.format_stack(frame)
            logger.error("!!!! setting %s to a non-int %s; please report this!", attr, value)
            logger.error("".join(stack_trace[:-1]))
            value = int(value)
        setattr(self, "_" + attr, value)

    return f


class XWindow:
    def __init__(self, conn, wid):
        self.conn = conn
        self.wid = wid

    def _property_string(self, r):
        """Extract a string from a window property reply message"""
        return r.value.to_string()

    def _property_utf8(self, r):
        try:
            return r.value.to_utf8()
        except UnicodeDecodeError:
            return r.value.to_string()

    def send_event(self, synthevent, mask=EventMask.NoEvent):
        self.conn.conn.core.SendEvent(False, self.wid, mask, synthevent.pack())

    def kill_client(self):
        self.conn.conn.core.KillClient(self.wid)

    def set_input_focus(self):
        self.conn.conn.core.SetInputFocus(
            xcffib.xproto.InputFocus.PointerRoot, self.wid, xcffib.xproto.Time.CurrentTime
        )

    def warp_pointer(self, x, y):
        """Warps the pointer to the location `x`, `y` on the window"""
        self.conn.conn.core.WarpPointer(
            0,
            self.wid,  # src_window, dst_window
            0,
            0,  # src_x, src_y
            0,
            0,  # src_width, src_height
            x,
            y,  # dest_x, dest_y
        )

    def get_name(self):
        """Tries to retrieve a canonical window name.

        We test the following properties in order of preference:
            - _NET_WM_VISIBLE_NAME
            - _NET_WM_NAME
            - WM_NAME.
        """
        r = self.get_property("_NET_WM_VISIBLE_NAME", "UTF8_STRING")
        if r:
            return self._property_utf8(r)

        r = self.get_property("_NET_WM_NAME", "UTF8_STRING")
        if r:
            return self._property_utf8(r)

        r = self.get_property(xcffib.xproto.Atom.WM_NAME, "UTF8_STRING")
        if r:
            return self._property_utf8(r)

        r = self.get_property(xcffib.xproto.Atom.WM_NAME, xcffib.xproto.GetPropertyType.Any)
        if r:
            return self._property_string(r)

    def get_wm_hints(self):
        wm_hints = self.get_property("WM_HINTS", xcffib.xproto.GetPropertyType.Any)
        if wm_hints:
            atoms_list = wm_hints.value.to_atoms()
            flags = {k for k, v in xcbq.HintsFlags.items() if atoms_list[0] & v}
            return {
                "flags": flags,
                "input": atoms_list[1] if "InputHint" in flags else None,
                "initial_state": atoms_list[2] if "StateHing" in flags else None,
                "icon_pixmap": atoms_list[3] if "IconPixmapHint" in flags else None,
                "icon_window": atoms_list[4] if "IconWindowHint" in flags else None,
                "icon_x": atoms_list[5] if "IconPositionHint" in flags else None,
                "icon_y": atoms_list[6] if "IconPositionHint" in flags else None,
                "icon_mask": atoms_list[7] if "IconMaskHint" in flags else None,
                "window_group": atoms_list[8] if "WindowGroupHint" in flags else None,
            }

    def get_wm_normal_hints(self):
        wm_normal_hints = self.get_property("WM_NORMAL_HINTS", xcffib.xproto.GetPropertyType.Any)
        if wm_normal_hints:
            atom_list = wm_normal_hints.value.to_atoms()
            flags = {k for k, v in xcbq.NormalHintsFlags.items() if atom_list[0] & v}
            hints = {
                "flags": flags,
                "min_width": atom_list[5],
                "min_height": atom_list[6],
                "max_width": atom_list[7],
                "max_height": atom_list[8],
                "width_inc": atom_list[9],
                "height_inc": atom_list[10],
                "min_aspect": (atom_list[11], atom_list[12]),
                "max_aspect": (atom_list[13], atom_list[14]),
            }

            # WM_SIZE_HINTS is potentially extensible (append to the end only)
            iterator = islice(hints, 15, None)
            hints["base_width"] = next(iterator, hints["min_width"])
            hints["base_height"] = next(iterator, hints["min_height"])
            hints["win_gravity"] = next(iterator, 1)
            return hints

    def get_wm_protocols(self):
        wm_protocols = self.get_property("WM_PROTOCOLS", "ATOM", unpack=int)
        if wm_protocols is not None:
            return {self.conn.atoms.get_name(wm_protocol) for wm_protocol in wm_protocols}
        return set()

    def get_wm_state(self):
        return self.get_property("WM_STATE", xcffib.xproto.GetPropertyType.Any, unpack=int)

    def get_wm_class(self):
        """Return an (instance, class) tuple if WM_CLASS exists."""
        r = self.get_property("WM_CLASS", "STRING")
        if r:
            s = self._property_string(r)
            return list(s.strip("\0").split("\0"))
        return []

    def get_wm_window_role(self):
        r = self.get_property("WM_WINDOW_ROLE", "STRING")
        if r:
            return self._property_string(r)

    def get_wm_transient_for(self):
        """Returns the WID of the parent window"""
        r = self.get_property("WM_TRANSIENT_FOR", "WINDOW", unpack=int)

        if r:
            return r[0]

    def get_wm_icon_name(self):
        r = self.get_property("_NET_WM_ICON_NAME", "UTF8_STRING")
        if r:
            return self._property_utf8(r)

        r = self.get_property("WM_ICON_NAME", "STRING")
        if r:
            return self._property_utf8(r)

    def get_wm_client_machine(self):
        r = self.get_property("WM_CLIENT_MACHINE", "STRING")
        if r:
            return self._property_utf8(r)

    def get_geometry(self):
        q = self.conn.conn.core.GetGeometry(self.wid)
        return q.reply()

    def get_wm_desktop(self):
        r = self.get_property("_NET_WM_DESKTOP", "CARDINAL", unpack=int)

        if r:
            return r[0]

    def get_wm_type(self):
        """
        http://standards.freedesktop.org/wm-spec/wm-spec-latest.html#id2551529
        """
        r = self.get_property("_NET_WM_WINDOW_TYPE", "ATOM", unpack=int)
        if r:
            first_name = None
            for i, a in enumerate(r):
                name = self.conn.atoms.get_name(a)
                if i == 0:
                    first_name = name
                qtile_type = xcbq.WindowTypes.get(name, None)
                if qtile_type is not None:
                    return qtile_type
            return first_name
        return None

    def get_net_wm_state(self):
        r = self.get_property("_NET_WM_STATE", "ATOM", unpack=int)
        if r:
            names = [self.conn.atoms.get_name(p) for p in r]
            return [xcbq.WindowStates.get(n, n) for n in names]
        return []

    def get_net_wm_pid(self):
        r = self.get_property("_NET_WM_PID", unpack=int)
        if r:
            return r[0]

    def configure(self, **kwargs):
        """
        Arguments can be: x, y, width, height, borderwidth, sibling, stackmode
        """
        mask, values = xcbq.ConfigureMasks(**kwargs)
        # older versions of xcb pack everything into unsigned ints "=I"
        # since 1.12, uses switches to pack things sensibly
        if float(".".join(xcffib.__xcb_proto_version__.split(".")[0:2])) < 1.12:
            values = [i & 0xFFFFFFFF for i in values]
        return self.conn.conn.core.ConfigureWindow(self.wid, mask, values)

    def set_attribute(self, **kwargs):
        mask, values = xcbq.AttributeMasks(**kwargs)
        self.conn.conn.core.ChangeWindowAttributesChecked(self.wid, mask, values)

    def set_cursor(self, name):
        cursor_id = self.conn.cursors[name]
        mask, values = xcbq.AttributeMasks(cursor=cursor_id)
        self.conn.conn.core.ChangeWindowAttributesChecked(self.wid, mask, values)

    def set_property(self, name, value, type=None, format=None):
        """
        Parameters
        ==========
        name: String Atom name
        type: String Atom name
        format: 8, 16, 32
        """
        if name in xcbq.PropertyMap:
            if type or format:
                raise ValueError("Over-riding default type or format for property.")
            type, format = xcbq.PropertyMap[name]
        else:
            if None in (type, format):
                raise ValueError("Must specify type and format for unknown property.")

        try:
            if isinstance(value, str):
                # xcffib will pack the bytes, but we should encode them properly
                value = value.encode()
            else:
                # if this runs without error, the value is already a list, don't wrap it
                next(iter(value))
        except StopIteration:
            # The value was an iterable, just empty
            value = []
        except TypeError:
            # the value wasn't an iterable and wasn't a string, so let's
            # wrap it.
            value = [value]

        try:
            self.conn.conn.core.ChangePropertyChecked(
                xcffib.xproto.PropMode.Replace,
                self.wid,
                self.conn.atoms[name],
                self.conn.atoms[type],
                format,  # Format - 8, 16, 32
                len(value),
                value,
            ).check()
        except xcffib.xproto.WindowError:
            logger.debug("X error in SetProperty (wid=%r, prop=%r), ignoring", self.wid, name)

    def get_property(self, prop, type=None, unpack=None):
        """Return the contents of a property as a GetPropertyReply

        If unpack is specified, a tuple of values is returned.  The type to
        unpack, either `str` or `int` must be specified.
        """
        if type is None:
            if prop not in xcbq.PropertyMap:
                raise ValueError("Must specify type for unknown property.")
            else:
                type, _ = xcbq.PropertyMap[prop]

        try:
            r = self.conn.conn.core.GetProperty(
                False,
                self.wid,
                self.conn.atoms[prop] if isinstance(prop, str) else prop,
                self.conn.atoms[type] if isinstance(type, str) else type,
                0,
                (2**32) - 1,
            ).reply()
        except (xcffib.xproto.WindowError, xcffib.xproto.AccessError):
            logger.debug("X error in GetProperty (wid=%r, prop=%r), ignoring", self.wid, prop)
            if unpack:
                return []
            return None

        if not r.value_len:
            if unpack:
                return []
            return None
        elif unpack:
            # Should we allow more options for unpacking?
            if unpack is int:
                return r.value.to_atoms()
            elif unpack is str:
                return r.value.to_string()
        else:
            return r

    def list_properties(self):
        r = self.conn.conn.core.ListProperties(self.wid).reply()
        return [self.conn.atoms.get_name(i) for i in r.atoms]

    def map(self):
        self.conn.conn.core.MapWindow(self.wid)

    def unmap(self):
        self.conn.conn.core.UnmapWindowUnchecked(self.wid)

    def get_attributes(self):
        return self.conn.conn.core.GetWindowAttributes(self.wid).reply()

    def query_tree(self):
        return self.conn.conn.core.QueryTree(self.wid).reply().children

    def paint_borders(self, depth, colors, borderwidth, width, height):
        """
        This method is used only by the managing Window class.
        """
        self.set_property("_NET_FRAME_EXTENTS", [borderwidth] * 4)

        if not colors or not borderwidth:
            return

        if isinstance(colors, str):
            self.set_attribute(borderpixel=self.conn.color_pixel(colors))
            return

        if len(colors) > borderwidth:
            colors = colors[:borderwidth]
        core = self.conn.conn.core
        outer_w = width + borderwidth * 2
        outer_h = height + borderwidth * 2

        with PixmapID(self.conn.conn) as pixmap:
            with GContextID(self.conn.conn) as gc:
                core.CreatePixmap(depth, pixmap, self.wid, outer_w, outer_h)
                core.CreateGC(gc, pixmap, 0, None)
                borders = len(colors)
                borderwidths = [borderwidth // borders] * borders
                for i in range(borderwidth % borders):
                    borderwidths[i] += 1
                coord = 0
                for i in range(borders):
                    core.ChangeGC(
                        gc, xcffib.xproto.GC.Foreground, [self.conn.color_pixel(colors[i])]
                    )
                    rect = xcffib.xproto.RECTANGLE.synthetic(
                        coord, coord, outer_w - coord * 2, outer_h - coord * 2
                    )
                    core.PolyFillRectangle(pixmap, gc, 1, [rect])
                    coord += borderwidths[i]
                self._set_borderpixmap(depth, pixmap, gc, borderwidth, width, height)

    def _set_borderpixmap(self, depth, pixmap, gc, borderwidth, width, height):
        core = self.conn.conn.core
        outer_w = width + borderwidth * 2
        outer_h = height + borderwidth * 2
        with PixmapID(self.conn.conn) as border:
            core.CreatePixmap(depth, border, self.wid, outer_w, outer_h)
            most_w = outer_w - borderwidth
            most_h = outer_h - borderwidth
            core.CopyArea(pixmap, border, gc, borderwidth, borderwidth, 0, 0, most_w, most_h)
            core.CopyArea(pixmap, border, gc, 0, 0, most_w, most_h, borderwidth, borderwidth)
            core.CopyArea(pixmap, border, gc, borderwidth, 0, 0, most_h, most_w, borderwidth)
            core.CopyArea(pixmap, border, gc, 0, borderwidth, most_w, 0, borderwidth, most_h)
            core.ChangeWindowAttributes(self.wid, xcffib.xproto.CW.BorderPixmap, [border])


class _Window:
    _window_mask = 0  # override in child class

    def __init__(self, window, qtile):
        base.Window.__init__(self)
        self.window, self.qtile = window, qtile
        self.hidden = False
        self.icons = {}
        window.set_attribute(eventmask=self._window_mask)
        self._group = None

        try:
            g = self.window.get_geometry()
            self._x = g.x
            self._y = g.y
            self._width = g.width
            self._height = g.height
            self._depth = g.depth
        except xcffib.xproto.DrawableError:
            # Whoops, we were too early, so let's ignore it for now and get the
            # values on demand.
            self._x = None
            self._y = None
            self._width = None
            self._height = None
            self._depth = None

        self.float_x: int | None = None
        self.float_y: int | None = None
        self._float_width: int = self._width
        self._float_height: int = self._height

        # We use `previous_layer` to see if a window has moved up or down a "layer"
        # The layers are defined in the spec:
        # https://specifications.freedesktop.org/wm-spec/1.3/ar01s07.html#STACKINGORDER
        # We assume a window starts off in the layer for "normal" windows, i.e. ones that
        # don't match the requirements to be in any of the other layers.
        self.previous_layer = (False, False, True, False, False, False)

        self.bordercolor = None
        self.state = NormalState
        self._float_state = FloatStates.NOT_FLOATING
        self._demands_attention = False

        self.hints = {
            "input": True,
            "icon_pixmap": None,
            "icon_window": None,
            "icon_x": 0,
            "icon_y": 0,
            "icon_mask": 0,
            "window_group": None,
            "urgent": False,
            # normal or size hints
            "width_inc": None,
            "height_inc": None,
            "base_width": 0,
            "base_height": 0,
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
    depth = property(
        fset=_geometry_setter("depth"),
        fget=_geometry_getter("depth"),
    )

    @property
    def wid(self):
        return self.window.wid

    @property
    def group(self):
        return self._group

    def has_fixed_ratio(self) -> bool:
        try:
            if (
                "PAspect" in self.hints["flags"]
                and self.hints["min_aspect"] == self.hints["max_aspect"]
            ):
                return True
        except KeyError:
            pass
        return False

    def has_fixed_size(self) -> bool:
        try:
            if (
                "PMinSize" in self.hints["flags"]
                and "PMaxSize" in self.hints["flags"]
                and 0 < self.hints["min_width"] == self.hints["max_width"]
                and 0 < self.hints["min_height"] == self.hints["max_height"]
            ):
                return True
        except KeyError:
            pass
        return False

    def has_user_set_position(self):
        try:
            if "USPosition" in self.hints["flags"] or "PPosition" in self.hints["flags"]:
                return True
        except KeyError:
            pass
        return False

    def update_name(self):
        try:
            self.name = self.window.get_name()
        except (xcffib.xproto.WindowError, xcffib.xproto.AccessError):
            return
        hook.fire("client_name_updated", self)

    def update_wm_class(self) -> None:
        self._wm_class = self.window.get_wm_class()

    def get_wm_class(self) -> list[str] | None:
        return self._wm_class

    def get_wm_type(self):
        return self.window.get_wm_type()

    def get_wm_role(self):
        return self.window.get_wm_window_role()

    def is_transient_for(self):
        """What window is this window a transient windor for?"""
        wid = self.window.get_wm_transient_for()
        return self.qtile.windows_map.get(wid)

    def update_hints(self):
        """Update the local copy of the window's WM_HINTS

        See http://tronche.com/gui/x/icccm/sec-4.html#WM_HINTS
        """
        try:
            h = self.window.get_wm_hints()
            normh = self.window.get_wm_normal_hints()
        except (xcffib.xproto.WindowError, xcffib.xproto.AccessError):
            return

        width_inc = self.hints["width_inc"]
        height_inc = self.hints["height_inc"]

        if normh:
            self.hints.update(normh)

        if h and "UrgencyHint" in h["flags"]:
            if self.qtile.current_window != self:
                self.hints["urgent"] = True
                hook.fire("client_urgent_hint_changed", self)
        elif self.urgent:
            self.hints["urgent"] = False
            hook.fire("client_urgent_hint_changed", self)

        if h and "InputHint" in h["flags"]:
            self.hints["input"] = h["input"]

        if (
            self.group
            and self.floating
            and width_inc != self.hints["width_inc"]
            and height_inc != self.hints["height_inc"]
        ):
            self.group.layout_all()

        return

    def update_state(self):
        triggered = ["urgent"]

        state = self.window.get_net_wm_state()

        if self.qtile.config.auto_fullscreen:
            triggered.append("fullscreen")
        # This might seem a bit weird but it's to workaround a bug in chromium based clients not properly redrawing
        # The bug is described in https://github.com/qtile/qtile/issues/4176
        # This only happens when auto fullscreen is set to false because we then do not obey the disable fullscreen state
        # So here we simply re-place the window at the coordinates which will magically solve the issue
        # This only seems to be an issue with unfullscreening, thus we check if we're fullscreen and the window wants to unfullscreen
        elif self.fullscreen and "fullscreen" not in state:
            self._reconfigure_floating(new_float_state=FloatStates.FULLSCREEN)

        for s in triggered:
            attr = s
            val = s in state
            if getattr(self, attr) != val:
                setattr(self, attr, val)

    @property
    def urgent(self):
        return self.hints["urgent"] or self._demands_attention

    @urgent.setter
    def urgent(self, val):
        self._demands_attention = val
        # TODO unset window hint as well?
        if not val:
            self.hints["urgent"] = False

    @expose_command()
    def info(self):
        if self.group:
            group = self.group.name
        else:
            group = None
        float_info = {
            "x": self.float_x,
            "y": self.float_y,
            "width": self._float_width,
            "height": self._float_height,
        }
        return dict(
            name=self.name,
            x=self.x,
            y=self.y,
            width=self.width,
            height=self.height,
            group=group,
            id=self.window.wid,
            wm_class=self.get_wm_class(),
            floating=self._float_state != FloatStates.NOT_FLOATING,
            float_info=float_info,
            maximized=self._float_state == FloatStates.MAXIMIZED,
            minimized=self._float_state == FloatStates.MINIMIZED,
            fullscreen=self._float_state == FloatStates.FULLSCREEN,
        )

    @property
    def state(self):
        return self.window.get_wm_state()[0]

    @state.setter
    def state(self, val):
        if val in (WithdrawnState, NormalState, IconicState):
            self.window.set_property("WM_STATE", [val, 0])

    @property
    def opacity(self):
        assert hasattr(self, "window")
        opacity = self.window.get_property("_NET_WM_WINDOW_OPACITY", unpack=int)
        if not opacity:
            return 1.0
        else:
            value = opacity[0]
            # 2 decimal places
            as_float = round(value / 0xFFFFFFFF, 2)
            return as_float

    @opacity.setter
    def opacity(self, opacity: float) -> None:
        if 0.0 <= opacity <= 1.0:
            real_opacity = int(opacity * 0xFFFFFFFF)
            assert hasattr(self, "window")
            self.window.set_property("_NET_WM_WINDOW_OPACITY", real_opacity)

    @expose_command()
    def kill(self):
        if "WM_DELETE_WINDOW" in self.window.get_wm_protocols():
            data = [
                self.qtile.core.conn.atoms["WM_DELETE_WINDOW"],
                xcffib.xproto.Time.CurrentTime,
                0,
                0,
                0,
            ]

            u = xcffib.xproto.ClientMessageData.synthetic(data, "I" * 5)

            e = xcffib.xproto.ClientMessageEvent.synthetic(
                format=32,
                window=self.window.wid,
                type=self.qtile.core.conn.atoms["WM_PROTOCOLS"],
                data=u,
            )

            self.window.send_event(e)
        else:
            self.window.kill_client()
        self.qtile.core.conn.flush()

    def hide(self):
        # We don't want to get the UnmapNotify for this unmap
        with self.disable_mask(EventMask.StructureNotify):
            with self.qtile.core.disable_unmap_events():
                self.window.unmap()
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
        self.window.set_attribute(eventmask=self._window_mask & (~mask))

    def _reset_mask(self):
        self.window.set_attribute(eventmask=self._window_mask)

    def _grab_click(self):
        # Grab buttons 1 - 3  to focus upon click when unfocussed
        for amask in self.qtile.core._auto_modmasks():
            for i in range(1, 4):
                self.qtile.core.conn.conn.core.GrabButton(
                    True,
                    self.window.wid,
                    EventMask.ButtonPress,
                    xcffib.xproto.GrabMode.Sync,
                    xcffib.xproto.GrabMode.Async,
                    xcffib.xproto.Atom._None,
                    xcffib.xproto.Atom._None,
                    i,
                    amask,
                )

    def _ungrab_click(self):
        # Ungrab buttons 1 - 3 when focussed
        self.qtile.core.conn.conn.core.UngrabButton(
            xcffib.xproto.Atom.Any,
            self.window.wid,
            xcffib.xproto.ModMask.Any,
        )

    def get_pid(self):
        return self.window.get_net_wm_pid()

    @expose_command()
    def place(
        self,
        x,
        y,
        width,
        height,
        borderwidth,
        bordercolor,
        above=False,
        margin=None,
        respect_hints=False,
    ):
        """
        Places the window at the specified location with the given size.

        Parameters
        ==========
        x: int
        y: int
        width: int
        height: int
        borderwidth: int
        bordercolor: string
        above: bool, optional
        margin: int or list, optional
            space around window as int or list of ints [N E S W]
        above: bool, optional
            If True, the geometry will be adjusted to respect hints provided by the
            client.
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

        # Optionally adjust geometry to respect client hints
        if respect_hints:
            flags = self.hints.get("flags", {})
            if "PMinSize" in flags:
                width = max(width, self.hints.get("min_width", 0))
                height = max(height, self.hints.get("min_height", 0))
            if "PMaxSize" in flags:
                width = min(width, self.hints.get("max_width", 0)) or width
                height = min(height, self.hints.get("max_height", 0)) or height
            if "PAspect" in flags and self._float_state == FloatStates.FLOATING:
                min_aspect = self.hints["min_aspect"]
                max_aspect = self.hints["max_aspect"]
                if width / height < min_aspect[0] / min_aspect[1]:
                    height = width * min_aspect[1] // min_aspect[0]
                elif width / height > max_aspect[0] / max_aspect[1]:
                    height = width * max_aspect[1] // max_aspect[0]

            if self.hints["base_width"] and self.hints["width_inc"]:
                width_adjustment = (width - self.hints["base_width"]) % self.hints["width_inc"]
                width -= width_adjustment
                if self.fullscreen:
                    x += int(width_adjustment / 2)

            if self.hints["base_height"] and self.hints["height_inc"]:
                height_adjustment = (height - self.hints["base_height"]) % self.hints[
                    "height_inc"
                ]
                height -= height_adjustment
                if self.fullscreen:
                    y += int(height_adjustment / 2)

        # save x and y float offset
        if self.group is not None and self.group.screen is not None:
            self.float_x = x - self.group.screen.x
            self.float_y = y - self.group.screen.y

        self.x = x
        self.y = y
        self.width = width
        self.height = height

        self.window.configure(x=x, y=y, width=width, height=height)

        if above:
            self.change_layer(up=True)

        self.paint_borders(bordercolor, borderwidth)

        if send_notify:
            self.send_configure_notify(x, y, width, height)

    def get_layering_information(self) -> tuple[bool, bool, bool, bool, bool, bool]:
        """
        Get layer-related EMWH-flags
        https://specifications.freedesktop.org/wm-spec/1.3/ar01s07.html#STACKINGORDER

        Copied here:

         To obtain good interoperability between different Desktop Environments,
         the following layered stacking order is recommended, from the bottom:

            - windows of type _NET_WM_TYPE_DESKTOP
            - windows having state _NET_WM_STATE_BELOW
            - windows not belonging in any other layer
            - windows of type _NET_WM_TYPE_DOCK (unless they have state
              _NET_WM_TYPE_BELOW) and windows having state _NET_WM_STATE_ABOVE
            - focused windows having state _NET_WM_STATE_FULLSCREEN

        Windows that are transient for another window should be kept above this window.

        The window manager may choose to put some windows in different stacking positions,
        for example to allow the user to bring currently a active window to the top and return
        it back when the window loses focus. To this end, qtile adds an additional layer so that
        scratchpad windows are placed above all others, always.
        """
        state = self.window.get_net_wm_state()
        _type = self.window.get_wm_type() or ""

        # Check if this window is focused
        active_window = self.qtile.core._root.get_property(
            "_NET_ACTIVE_WINDOW", "WINDOW", unpack=int
        )
        if active_window and active_window[0] == self.window.wid:
            focus = True
        else:
            focus = False

        desktop = _type == "desktop"
        below = "_NET_WM_STATE_BELOW" in state
        dock = _type == "dock"
        above = "_NET_WM_STATE_ABOVE" in state
        full = (
            "fullscreen" in state
        )  # get_net_wm_state translates this state so we don't use _NET_WM name
        is_scratchpad = isinstance(self.qtile.groups_map.get(self.group), ScratchPad)

        # sort the flags from bottom to top, True meaning further below than False at each step
        states = [desktop, below, above or (dock and not below), full and focus, is_scratchpad]
        other = not any(states)
        states.insert(2, other)

        # If we're a desktop, this should always be the lowest layer...
        if desktop:
            # mypy can't work out that this gives us tuple[bool, bool, bool, bool, bool, bool]...
            # (True, False, False, False, False, False)
            return tuple(not i for i in range(6))  # type: ignore

        # ...otherwise, we set to the highest matching layer.
        # Look for the highest matching level and then set all other levels to False
        highest = max(i for i, state in enumerate(states) if state)

        # mypy can't work out that this gives us tuple[bool, bool, bool, bool, bool, bool]...
        return tuple(i == highest for i in range(6))  # type: ignore

    def change_layer(self, up=True, top_bottom=False):
        """Raise a window above its peers or move it below them, depending on 'up'.
        Raising a normal window will not lift it above pinned windows etc.

        There are a few important things to take note of when relaying windows:
        1. If a window has a defined parent, it should not be moved underneath it.
           In case children are blocking, this could leave an application in an unusable state.
        2. If a window has children, they should be moved along with it.
        3. If a window has a defined parent, either move the parent or do nothing at all.
        4. EMWH-flags follow strict layering rules:
           https://specifications.freedesktop.org/wm-spec/1.3/ar01s07.html#STACKINGORDER
        """
        if len(self.qtile.windows_map) < 2:
            return

        if self.group is None and not isinstance(self, Static):
            return

        # Use the window's group or current group if this isn't set (e.g. Static windows)
        group = self.group or self.qtile.current_group

        parent = self.window.get_wm_transient_for()
        if parent is not None and not up:
            return

        layering = self.get_layering_information()

        # Comparison of layer states: -1 if window is now in a lower state group,
        # 0 if it's in the same group and 1 if it's in a higher group
        moved = (self.previous_layer > layering) - (layering > self.previous_layer)
        self.previous_layer = layering

        stack = list(self.qtile.core._root.query_tree())
        if self.wid not in stack or len(stack) < 2:
            return

        # Get all windows for the group and add Static windows to ensure these are included
        # in the stacking
        group_windows = group.windows.copy()
        statics = [win for win in self.qtile.windows_map.values() if isinstance(win, Static)]
        group_windows.extend(statics)

        if group.screen is not None:
            group_bars = [gap for gap in group.screen.gaps if isinstance(gap, bar.Bar)]
        else:
            group_bars = []

        # Get list of windows that are in the stack and managed by qtile
        # List of tuples (XWindow object, transient_for, layering_information)
        windows = list(
            map(
                lambda w: (
                    w.window,
                    w.window.get_wm_transient_for(),
                    w.get_layering_information(),
                ),
                group_windows,
            )
        )

        # Remove any windows that aren't in the server's stack
        windows = list(filter(lambda w: w[0].wid in stack, windows))

        # Sort this list to match stacking order reported by server
        windows.sort(key=lambda w: stack.index(w[0].wid))

        # Get lists of windows on lower, higher or same "layer" as window
        lower = [w[0].wid for w in windows if w[2] > layering]
        higher = [w[0].wid for w in windows if w[2] < layering]
        same = [w[0].wid for w in windows if w[2] == layering]

        # We now need to identify the new position in the stack

        # If the window has a parent, the window should just be put above it
        # If the parent isn't being managed by qtile then it may not be stacked correctly
        if parent and parent in self.qtile.windows_map:
            # If the window is modal then it should be placed above every other window that is in that window group
            # e.g. the parent of the dialog and any other window that is also transient for the same parent.
            if "_NET_WM_STATE_MODAL" in self.window.get_net_wm_state():
                window_group = [parent]
                window_group.extend(
                    k
                    for k, v in self.qtile.windows_map.items()
                    if v.window.get_wm_transient_for() == parent
                )
                window_group.sort(key=stack.index)

                # Make sure we're above the last window in that group
                sibling = window_group[-1]

            else:
                sibling = parent

            above = True

        # Now we just check whether the window has changed layer.

        # If we're forcing to top or bottom of current layer...
        elif top_bottom:
            # If there are no other windows in the same layer then there's nothing to do
            if not same:
                return

            if up:
                sibling = same[-1]
                above = True
            else:
                sibling = same[0]
                above = False

        # There are no windows in the desired layer (should never happen) or
        # we've moved to a new layer and are the only window in that layer
        elif not same or (len(same) == 1 and moved != 0):
            # Try to put it above the last window in the lower layers
            if lower:
                sibling = lower[-1]
                above = True

            # Or below the first window in the higher layers
            elif higher:
                sibling = higher[0]
                above = False

            # Don't think we should end up here but, if we do...
            else:
                # Put the window above the highest window if we're raising it
                if up:
                    sibling = stack[-1]
                    above = True

                # or below the lowest window if we're lowering the window
                else:
                    sibling = stack[0]
                    above = False

        else:
            # Window has moved to a lower layer state
            if moved < 0:
                if self.kept_below:
                    sibling = same[0]
                    above = False
                else:
                    sibling = same[-1]
                    above = True

            # Window is in same layer state
            elif moved == 0:
                try:
                    pos = same.index(self.wid)
                except ValueError:
                    pos = len(same) if up else 0
                if not up:
                    pos = max(0, pos - 1)
                else:
                    pos = min(pos + 1, len(same) - 1)
                sibling = same[pos]
                above = up

            # Window is in a higher layer
            else:
                if self.kept_above:
                    sibling = same[-1]
                    above = True
                else:
                    sibling = same[0]
                    above = False

        # If the sibling is the current window then we just check if any windows in lower/higher layers are
        # stacked incorrectly and, if so, restack them. However, we don't need to configure stacking for this
        # window
        if sibling == self.wid:
            index = stack.index(self.wid)

            # We need to make sure the bars are included so add them now
            if group_bars:
                for group_bar in group_bars:
                    bar_layer = group_bar.window.get_layering_information()
                    if bar_layer > layering:
                        lower.append(group_bar.window.wid)
                    elif bar_layer < layering:
                        higher.append(group_bar.window.wid)

                # Sort the list to match the server's stacking order
                lower.sort(key=lambda wid: stack.index(wid))
                higher.sort(key=lambda wid: stack.index(wid))

            for wid in [w for w in lower if stack.index(w) > index]:
                self.qtile.windows_map[wid].window.configure(
                    stackmode=xcffib.xproto.StackMode.Below, sibling=same[0]
                )

            # We reverse higher as each window will be placed above the last item in the current layer
            # this means the last item we stack will be just above the current layer.
            for wid in [w for w in higher[::-1] if stack.index(w) < index]:
                self.qtile.windows_map[wid].window.configure(
                    stackmode=xcffib.xproto.StackMode.Above, sibling=same[-1]
                )

            return

        # Window needs new stacking info. We tell the server to stack the window
        # above or below a given "sibling"
        self.window.configure(
            stackmode=xcffib.xproto.StackMode.Above if above else xcffib.xproto.StackMode.Below,
            sibling=sibling,
        )

        # Move window's children if we were moved upwards
        if above:
            self.raise_children(stack=stack)

        self.qtile.core.update_client_lists()

    def raise_children(self, stack=None):
        """Ensure any transient windows are moved up with the parent."""
        children = [
            k
            for k, v in self.qtile.windows_map.items()
            if v.window.get_wm_transient_for() == self.window.wid
        ]
        if children:
            if stack is None:
                stack = list(self.qtile.core._root.query_tree())
            parent = self.window.wid
            children.sort(key=stack.index)
            for child in children:
                self.qtile.windows_map[child].window.configure(
                    stackmode=xcffib.xproto.StackMode.Above, sibling=parent
                )
                parent = child

    def paint_borders(self, color, width):
        self.borderwidth = width
        self.bordercolor = color
        self.window.configure(borderwidth=width)
        self.window.paint_borders(self.depth, color, width, self.width, self.height)

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
            override_redirect=override_redirect,
        )

        self.window.send_event(event, mask=EventMask.StructureNotify)

    @property
    def can_steal_focus(self):
        return super().can_steal_focus and self.window.get_wm_type() != "notification"

    @can_steal_focus.setter
    def can_steal_focus(self, can_steal_focus: bool) -> None:
        self._can_steal_focus = can_steal_focus

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
        if self.hints["input"]:
            self.window.set_input_focus()
            return True

        # does the window want us to ask it about focus?
        if "WM_TAKE_FOCUS" in self.window.get_wm_protocols():
            data = [
                self.qtile.core.conn.atoms["WM_TAKE_FOCUS"],
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
                0,
            ]

            u = xcffib.xproto.ClientMessageData.synthetic(data, "I" * 5)
            e = xcffib.xproto.ClientMessageEvent.synthetic(
                format=32,
                window=self.window.wid,
                type=self.qtile.core.conn.atoms["WM_PROTOCOLS"],
                data=u,
            )

            self.window.send_event(e)
            return True

        # we didn't focus this time. but now the window knows if it wants
        # focus, it should SetFocus() itself; we'll get another notification
        # about this.
        return False

    @expose_command()
    def focus(self, warp: bool = True) -> None:
        """Focuses the window."""
        did_focus = self._do_focus()
        if not did_focus:
            return

        # now, do all the other WM stuff since the focus actually changed
        if warp and self.qtile.config.cursor_warp:
            self.window.warp_pointer(self.width // 2, self.height // 2)

        # update net wm state
        state = list(self.window.get_property("_NET_WM_STATE", "ATOM", unpack=int))
        state_focused = self.qtile.core.conn.atoms["_NET_WM_STATE_FOCUSED"]
        state.append(state_focused)

        if self.urgent:
            self.urgent = False
            atom = self.qtile.core.conn.atoms["_NET_WM_STATE_DEMANDS_ATTENTION"]

            if atom in state:
                state.remove(atom)

        self.window.set_property("_NET_WM_STATE", state)

        # re-grab button events on the previously focussed window
        old = self.qtile.core._root.get_property("_NET_ACTIVE_WINDOW", "WINDOW", unpack=int)
        if old and old[0] in self.qtile.windows_map:
            old_win = self.qtile.windows_map[old[0]]
            if not isinstance(old_win, base.Internal):
                old_win._grab_click()
                state = list(old_win.window.get_property("_NET_WM_STATE", "ATOM", unpack=int))
                if state_focused in state:
                    state.remove(state_focused)
                    old_win.window.set_property("_NET_WM_STATE", state)
        self.qtile.core._root.set_property("_NET_ACTIVE_WINDOW", self.window.wid)
        self._ungrab_click()

        # Check if we need to restack a previously focused fullscreen window
        self.qtile.core.check_stacking(self)

        if self.group and self.group.current_window is not self:
            self.group.focus(self)

        hook.fire("client_focus", self)

    @expose_command()
    def get_hints(self):
        """Returns the X11 hints (WM_HINTS and WM_SIZE_HINTS) for this window."""
        return self.hints

    @expose_command()
    def inspect(self):
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
            "do_not_propagate_mask": a.do_not_propagate_mask,
        }
        props = self.window.list_properties()
        normalhints = self.window.get_wm_normal_hints()
        hints = self.window.get_wm_hints()
        protocols = []
        for i in self.window.get_wm_protocols():
            protocols.append(i)

        state = self.window.get_wm_state()

        float_info = {
            "x": self.float_x,
            "y": self.float_y,
            "width": self._float_width,
            "height": self._float_height,
        }

        return dict(
            attributes=attrs,
            properties=props,
            name=self.window.get_name(),
            wm_class=self.get_wm_class(),
            wm_window_role=self.window.get_wm_window_role(),
            wm_type=self.window.get_wm_type(),
            wm_transient_for=self.window.get_wm_transient_for(),
            protocols=protocols,
            wm_icon_name=self.window.get_wm_icon_name(),
            wm_client_machine=self.window.get_wm_client_machine(),
            normalhints=normalhints,
            hints=hints,
            state=state,
            float_info=float_info,
        )

    @expose_command()
    def keep_above(self, enable: bool | None = None):
        if enable is None:
            self.kept_above = not self.kept_above
        else:
            self.kept_above = enable

        self.change_layer(top_bottom=True, up=True)

    @expose_command()
    def keep_below(self, enable: bool | None = None):
        if enable is None:
            self.kept_below = not self.kept_below
        else:
            self.kept_below = enable

        self.change_layer(top_bottom=True, up=False)

    @expose_command()
    def move_up(self, force=False):
        if self.kept_below and force:
            self.kept_below = False
        with self.qtile.core.masked():
            # Disable masks so that moving windows along the Z axis doesn't trigger
            # focus change events (i.e. due to `follow_mouse_focus`)
            self.change_layer()

    @expose_command()
    def move_down(self, force=False):
        if self.kept_above and force:
            self.kept_above = False
        with self.qtile.core.masked():
            self.change_layer(up=False)

    @expose_command()
    def move_to_top(self, force=False):
        if self.kept_below and force:
            self.kept_below = False
        with self.qtile.core.masked():
            self.change_layer(top_bottom=True)

    @expose_command()
    def move_to_bottom(self, force=False):
        if self.kept_above and force:
            self.kept_above = False
        with self.qtile.core.masked():
            self.change_layer(up=False, top_bottom=True)

    @property
    def kept_above(self):
        reply = list(self.window.get_property("_NET_WM_STATE", "ATOM", unpack=int))
        atom = self.qtile.core.conn.atoms["_NET_WM_STATE_ABOVE"]
        return atom in reply

    @kept_above.setter
    def kept_above(self, value):
        reply = list(self.window.get_property("_NET_WM_STATE", "ATOM", unpack=int))
        atom = self.qtile.core.conn.atoms["_NET_WM_STATE_ABOVE"]
        if value and atom not in reply:
            reply.append(atom)
        elif not value and atom in reply:
            reply.remove(atom)
        else:
            return
        atom = self.qtile.core.conn.atoms["_NET_WM_STATE_BELOW"]
        if atom in reply:
            reply.remove(atom)
        self.window.set_property("_NET_WM_STATE", reply)
        self.change_layer()

    @property
    def kept_below(self):
        reply = list(self.window.get_property("_NET_WM_STATE", "ATOM", unpack=int))
        atom = self.qtile.core.conn.atoms["_NET_WM_STATE_BELOW"]
        return atom in reply

    @kept_below.setter
    def kept_below(self, value):
        reply = list(self.window.get_property("_NET_WM_STATE", "ATOM", unpack=int))
        atom = self.qtile.core.conn.atoms["_NET_WM_STATE_BELOW"]
        if value and atom not in reply:
            reply.append(atom)
        elif not value and atom in reply:
            reply.remove(atom)
        else:
            return
        atom = self.qtile.core.conn.atoms["_NET_WM_STATE_ABOVE"]
        if atom in reply:
            reply.remove(atom)
        self.window.set_property("_NET_WM_STATE", reply)
        self.change_layer(up=False)

    @expose_command()
    def bring_to_front(self):
        if self.get_wm_type() != "desktop":
            self.window.configure(stackmode=xcffib.xproto.StackMode.Above)
            self.raise_children()
            self.qtile.core.update_client_lists()


class Internal(_Window, base.Internal):
    """An internal window, that should not be managed by qtile"""

    _window_mask = (
        EventMask.StructureNotify
        | EventMask.PropertyChange
        | EventMask.EnterWindow
        | EventMask.LeaveWindow
        | EventMask.PointerMotion
        | EventMask.FocusChange
        | EventMask.Exposure
        | EventMask.ButtonPress
        | EventMask.ButtonRelease
        | EventMask.KeyPress
    )

    def __init__(self, win, qtile, desired_depth=32):
        _Window.__init__(self, win, qtile)
        win.set_property("QTILE_INTERNAL", 1)
        self._depth = desired_depth

    def create_drawer(self, width: int, height: int) -> Drawer:
        """Create a Drawer that draws to this window."""
        return Drawer(self.qtile, self, width, height)

    @expose_command()
    def kill(self):
        if self.window.wid in self.qtile.windows_map:
            # It will be present during config reloads; absent during shutdown as this
            # will follow graceful_shutdown
            with contextlib.suppress(xcffib.ConnectionException):
                self.qtile.core.conn.conn.core.DestroyWindow(self.window.wid)

    def handle_Expose(self, e):  # noqa: N802
        self.process_window_expose()

    def handle_ButtonPress(self, e):  # noqa: N802
        self.process_button_click(e.event_x, e.event_y, e.detail)

    def handle_ButtonRelease(self, e):  # noqa: N802
        self.process_button_release(e.event_x, e.event_y, e.detail)
        # return True to ensure Core also processes the release
        return True

    def handle_EnterNotify(self, e):  # noqa: N802
        self.process_pointer_enter(e.event_x, e.event_y)

    def handle_LeaveNotify(self, e):  # noqa: N802
        self.process_pointer_leave(e.event_x, e.event_y)

    def handle_MotionNotify(self, e):  # noqa: N802
        self.process_pointer_motion(e.event_x, e.event_y)

    def handle_KeyPress(self, e):  # noqa: N802
        mask = xcbq.ModMasks["shift"] | xcbq.ModMasks["lock"]
        state = 1 if e.state & mask else 0
        keysym = self.qtile.core.conn.code_to_syms[e.detail][state]
        self.process_key_press(keysym)

    def info(self):
        return dict(
            x=self.x,
            y=self.y,
            width=self.width,
            height=self.height,
            id=self.window.wid,
        )

    @expose_command()
    def focus(self, warp: bool = True) -> None:
        """Focuses the window."""
        self._do_focus()


class Static(_Window, base.Static):
    """An static window, belonging to a screen rather than a group"""

    _window_mask = (
        EventMask.StructureNotify
        | EventMask.PropertyChange
        | EventMask.EnterWindow
        | EventMask.FocusChange
        | EventMask.Exposure
    )

    def __init__(self, win, qtile, screen, x=None, y=None, width=None, height=None):
        _Window.__init__(self, win, qtile)
        self._wm_class: list[str] | None = None
        self.update_wm_class()
        self.update_name()
        self.conf_x = x
        self.conf_y = y
        self.conf_width = width
        self.conf_height = height
        x = x or self.x
        y = y or self.y
        self.x = x + screen.x
        self.y = y + screen.y
        self.screen = screen
        self.place(self.x, self.y, width or self.width, height or self.height, 0, 0)
        self.unhide()
        self.update_strut()
        self._grab_click()

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
            self.x,
            self.y,
            self.width,
            self.height,
            self.borderwidth,
            self.bordercolor,
        )
        return False

    def update_strut(self):
        strut = self.window.get_property("_NET_WM_STRUT_PARTIAL", unpack=int)
        if strut:
            x_screen_dimensions = self.qtile.core._root.get_geometry()
            if strut[0]:  # left
                x = strut[0]
                y = (strut[4] + strut[5]) / 2 or (strut[6] + strut[7]) / 2
            elif strut[1]:  # right
                x = x_screen_dimensions.width - strut[1]
                y = (strut[4] + strut[5]) / 2 or (strut[6] + strut[7]) / 2
            elif strut[2]:  # top
                x = (strut[8] + strut[9]) / 2 or (strut[10] + strut[11]) / 2
                y = strut[2]
            else:  # bottom
                x = (strut[8] + strut[9]) / 2 or (strut[10] + strut[11]) / 2
                y = x_screen_dimensions.height - strut[3]
            self.screen = self.qtile.find_screen(x, y)

            if self.screen is None:
                logger.error("No screen at target")
                return
            elif None in [self.screen.x, self.screen.y, self.screen.height, self.screen.width]:
                logger.error("Missing screen information")
                return

            empty_space = [
                self.screen.x,
                x_screen_dimensions.width - self.screen.x - self.screen.width,
                self.screen.y,
                x_screen_dimensions.height - self.screen.y - self.screen.height,
            ]
            self.reserved_space = tuple(
                strut[i] - empty if strut[i] else 0 for i, empty in enumerate(empty_space)
            )

            self.qtile.reserve_space(self.reserved_space, self.screen)

        else:
            self.reserved_space = None

    def handle_PropertyNotify(self, e):  # noqa: N802
        name = self.qtile.core.conn.atoms.get_name(e.atom)
        if name == "_NET_WM_STRUT_PARTIAL":
            self.update_strut()


class Window(_Window, base.Window):
    _window_mask = (
        EventMask.StructureNotify
        | EventMask.PropertyChange
        | EventMask.EnterWindow
        | EventMask.FocusChange
    )

    def __init__(self, window, qtile):
        _Window.__init__(self, window, qtile)
        self._wm_class: list[str] | None = None
        self.update_wm_class()
        self.update_name()
        self.set_group()

        # add window to the save-set, so it gets mapped when qtile dies
        qtile.core.conn.conn.core.ChangeSaveSet(SetMode.Insert, self.window.wid)
        self.update_wm_net_icon()
        self._grab_click()

    @property
    def group(self):
        return self._group

    @group.setter
    def group(self, group):
        if group:
            try:
                self.window.set_property("_NET_WM_DESKTOP", self.qtile.groups.index(group))
            except xcffib.xproto.WindowError:
                logger.exception("whoops, got error setting _NET_WM_DESKTOP, too early?")
        self._group = group

    @property
    def edges(self):
        return (self.x, self.y, self.x + self.width, self.y + self.height)

    @property
    def floating(self):
        return self._float_state != FloatStates.NOT_FLOATING

    @floating.setter
    def floating(self, do_float):
        stack = self.qtile.core._root.query_tree()
        tiled = [win.window.wid for win in (self.group.tiled_windows if self.group else [])]
        tiled_stack = [wid for wid in stack if wid in tiled and wid != self.window.wid]
        if do_float and self._float_state == FloatStates.NOT_FLOATING:
            if self.is_placed():
                screen = self.group.screen
                self._enablefloating(
                    screen.x + self.float_x,
                    screen.y + self.float_y,
                    self._float_width,
                    self._float_height,
                )

                # Make sure floating window is placed above tiled windows
                if tiled_stack and (not self.kept_above or self.qtile.config.floats_kept_above):
                    stack_list = list(stack)
                    highest_tile = tiled_stack[-1]
                    if stack_list.index(self.window.wid) < stack_list.index(highest_tile):
                        self.window.configure(
                            stackmode=xcffib.xproto.StackMode.Above, sibling=highest_tile
                        )
            else:
                # if we are setting floating early, e.g. from a hook, we don't have a screen yet
                self._float_state = FloatStates.FLOATING
            if not self.kept_above and self.qtile.config.floats_kept_above:
                self.keep_above(enable=True)

        elif (not do_float) and self._float_state != FloatStates.NOT_FLOATING:
            self.update_fullscreen_wm_state(False)
            if self._float_state == FloatStates.FLOATING:
                # store last size
                self._float_width = self.width
                self._float_height = self.height
            self._float_state = FloatStates.NOT_FLOATING
            self.group.mark_floating(self, False)
            if tiled_stack:
                self.window.configure(
                    stackmode=xcffib.xproto.StackMode.Above, sibling=tiled_stack[-1]
                )
            hook.fire("float_change")

    @property
    def wants_to_fullscreen(self):
        try:
            return "fullscreen" in self.window.get_net_wm_state()
        except (xcffib.xproto.WindowError, xcffib.xproto.AccessError):
            pass
        return False

    @expose_command()
    def toggle_floating(self):
        self.floating = not self.floating

    def set_wm_state(self, old_state, new_state):
        if new_state != old_state:
            self.window.set_property("_NET_WM_STATE", list(new_state))

    def update_fullscreen_wm_state(self, do_full):
        # already done updating previously
        if do_full == self.fullscreen:
            return

        # update fullscreen _NET_WM_STATE
        atom = set([self.qtile.core.conn.atoms["_NET_WM_STATE_FULLSCREEN"]])
        prev_state = set(self.window.get_property("_NET_WM_STATE", "ATOM", unpack=int))

        if do_full:
            self.set_wm_state(prev_state, prev_state | atom)
        else:
            self.set_wm_state(prev_state, prev_state - atom)

    @property
    def fullscreen(self):
        return self._float_state == FloatStates.FULLSCREEN

    @fullscreen.setter
    def fullscreen(self, do_full):
        if do_full:
            needs_change = self._float_state != FloatStates.FULLSCREEN
            screen = self.group.screen or self.qtile.find_closest_screen(self.x, self.y)

            if self._float_state not in (FloatStates.MAXIMIZED, FloatStates.FULLSCREEN):
                self._save_geometry()

            bw = self.group.floating_layout.fullscreen_border_width
            self._enablefloating(
                screen.x,
                screen.y,
                screen.width - 2 * bw,
                screen.height - 2 * bw,
                new_float_state=FloatStates.FULLSCREEN,
            )
            # Only restack layers if floating state has changed
            if needs_change:
                self.change_layer()
            return

        if self._float_state == FloatStates.FULLSCREEN:
            self._restore_geometry()
            self.floating = False
            self.change_layer()
            return

    @property
    def maximized(self):
        return self._float_state == FloatStates.MAXIMIZED

    @maximized.setter
    def maximized(self, do_maximize):
        if do_maximize:
            screen = self.group.screen or self.qtile.find_closest_screen(self.x, self.y)

            if self._float_state not in (FloatStates.MAXIMIZED, FloatStates.FULLSCREEN):
                self._save_geometry()

            bw = self.group.floating_layout.max_border_width
            self._enablefloating(
                screen.dx,
                screen.dy,
                screen.dwidth - 2 * bw,
                screen.dheight - 2 * bw,
                new_float_state=FloatStates.MAXIMIZED,
            )
        else:
            if self._float_state == FloatStates.MAXIMIZED:
                self._restore_geometry()
                self.floating = False

    @property
    def minimized(self):
        return self._float_state == FloatStates.MINIMIZED

    @minimized.setter
    def minimized(self, do_minimize):
        if do_minimize:
            if self._float_state != FloatStates.MINIMIZED:
                self._enablefloating(new_float_state=FloatStates.MINIMIZED)
        else:
            if self._float_state == FloatStates.MINIMIZED:
                self.floating = False

    @expose_command()
    def toggle_minimize(self):
        self.minimized = not self.minimized

    @expose_command()
    def is_visible(self) -> bool:
        return not self.hidden and not self.minimized

    @expose_command()
    def static(
        self,
        screen: int | None = None,
        x: int | None = None,
        y: int | None = None,
        width: int | None = None,
        height: int | None = None,
    ) -> None:
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
        self.qtile.core.update_client_lists()
        hook.fire("client_managed", s)

    def tweak_float(self, x=None, y=None, dx=0, dy=0, w=None, h=None, dw=0, dh=0):
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

    @expose_command()
    def get_size(self):
        return (self.width, self.height)

    @expose_command()
    def get_position(self):
        return (self.x, self.y)

    def _reconfigure_floating(self, new_float_state=FloatStates.FLOATING):
        self.update_fullscreen_wm_state(new_float_state == FloatStates.FULLSCREEN)
        if new_float_state == FloatStates.MINIMIZED:
            self.state = IconicState
            self.hide()
        else:
            self.place(
                self.x,
                self.y,
                self.width,
                self.height,
                self.borderwidth,
                self.bordercolor,
                above=False,
                respect_hints=True,
            )
        if self._float_state != new_float_state:
            self._float_state = new_float_state
            if self.group:  # may be not, if it's called from hook
                self.group.mark_floating(self, True)
            if new_float_state == FloatStates.FLOATING:
                if self.qtile.config.floats_kept_above:
                    self.keep_above(enable=True)
            elif new_float_state == FloatStates.MAXIMIZED:
                self.move_to_top()
            hook.fire("float_change")

    def _enablefloating(
        self, x=None, y=None, w=None, h=None, new_float_state=FloatStates.FLOATING
    ):
        if new_float_state != FloatStates.MINIMIZED:
            self.x = x
            self.y = y
            self.width = w
            self.height = h
        self._reconfigure_floating(new_float_state=new_float_state)

    def set_group(self):
        # add to group by position according to _NET_WM_DESKTOP property
        group = None
        index = self.window.get_wm_desktop()

        if index is not None and index < len(self.qtile.groups):
            group = self.qtile.groups[index]
        elif index is None:
            transient_for = self.is_transient_for()
            if transient_for is not None:
                group = transient_for._group
        if group is not None:
            group.add(self)
            self._group = group
            if group != self.qtile.current_screen.group:
                self.hide()

    @expose_command()
    def togroup(self, group_name=None, *, switch_group=False, toggle=False):
        """Move window to a specified group

        Also switch to that group if switch_group is True.

        If `toggle` is True and and the specified group is already on the screen,
        use the last used group as target instead.
        """
        if group_name is None:
            group = self.qtile.current_group
        else:
            group = self.qtile.groups_map.get(group_name)
            if group is None:
                raise CommandError(f"No such group: {group_name}")

        if self.group is group:
            if toggle and self.group.screen.previous_group:
                group = self.group.screen.previous_group
            else:
                return

        self.hide()
        if self.group:
            if self.group.screen:
                # for floats remove window offset
                self.x -= self.group.screen.x
            group_ref = self.group
            self.group.remove(self)
            if (
                not self.qtile.dgroups.groups_map[group_ref.name].persist
                and len(group_ref.windows) <= 1
            ):
                # set back original group so _del() can grab it
                self.group = group_ref
                self.qtile.dgroups._del(self)
                self.group = None

        if group.screen and self.x < group.screen.x:
            self.x += group.screen.x
        group.add(self)
        if switch_group:
            group.toscreen(toggle=toggle)

    @expose_command()
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
        if self.qtile.config.follow_mouse_focus is True:
            if self.group.current_window != self:
                self.group.focus(self, False)
            if self.group.screen and self.qtile.current_screen != self.group.screen:
                self.qtile.focus_screen(self.group.screen.index, False)
        return True

    def handle_ButtonPress(self, e):  # noqa: N802
        self.qtile.core.focus_by_click(e, window=self)
        self.qtile.core.conn.conn.core.AllowEvents(xcffib.xproto.Allow.ReplayPointer, e.time)

    def handle_ConfigureRequest(self, e):  # noqa: N802
        if self.qtile._drag and self.qtile.current_window == self:
            # ignore requests while user is dragging window
            return
        if getattr(self, "floating", False):
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
                x,
                y,
                width,
                height,
                self.borderwidth,
                self.bordercolor,
            )
        self.update_state()
        return False

    def update_wm_net_icon(self):
        """Set a dict with the icons of the window"""

        icon = self.window.get_property("_NET_WM_ICON", "CARDINAL")
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
                mult = arr[i + 3] / 255.0
                arr[i + 0] = int(arr[i + 0] * mult)
                arr[i + 1] = int(arr[i + 1] * mult)
                arr[i + 2] = int(arr[i + 2] * mult)
            icon = icon[next_pix:]
            icons[f"{width}x{height}"] = arr
        self.icons = icons
        hook.fire("net_wm_icon_change", self)

    def handle_ClientMessage(self, event):  # noqa: N802
        atoms = self.qtile.core.conn.atoms

        opcode = event.type
        data = event.data
        if atoms["_NET_WM_STATE"] == opcode:
            prev_state = self.window.get_property("_NET_WM_STATE", "ATOM", unpack=int)

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

            self.window.set_property("_NET_WM_STATE", list(current_state))
        elif atoms["_NET_ACTIVE_WINDOW"] == opcode:
            source = data.data32[0]
            if source == 2:  # XCB_EWMH_CLIENT_SOURCE_TYPE_NORMAL
                logger.debug("Focusing window by pager")
                self.qtile.current_screen.set_group(self.group)
                self.group.focus(self)
                self.bring_to_front()
            else:  # XCB_EWMH_CLIENT_SOURCE_TYPE_OTHER
                focus_behavior = self.qtile.config.focus_on_window_activation
                if (
                    focus_behavior == "focus"
                    or type(focus_behavior) is FunctionType
                    and focus_behavior(self)
                ):
                    logger.debug("Focusing window")
                    # Windows belonging to a scratchpad need to be toggled properly
                    if isinstance(self.group, ScratchPad):
                        for dropdown in self.group.dropdowns.values():
                            if dropdown.window is self:
                                dropdown.show()
                                break
                    else:
                        self.qtile.current_screen.set_group(self.group)
                        self.group.focus(self)
                elif focus_behavior == "smart":
                    if not self.group.screen:
                        logger.debug(
                            "Ignoring focus request (focus_on_window_activation='smart')"
                        )
                        return
                    if self.group.screen == self.qtile.current_screen:
                        logger.debug("Focusing window")
                        # Windows belonging to a scratchpad need to be toggled properly
                        if isinstance(self.group, ScratchPad):
                            for dropdown in self.group.dropdowns.values():
                                if dropdown.window is self:
                                    dropdown.show()
                                    break
                        else:
                            self.qtile.current_screen.set_group(self.group)
                            self.group.focus(self)
                    else:  # self.group.screen != self.qtile.current_screen:
                        logger.debug("Setting urgent flag for window")
                        self.urgent = True
                        hook.fire("client_urgent_hint_changed", self)
                elif focus_behavior == "urgent":
                    logger.debug("Setting urgent flag for window")
                    self.urgent = True
                    hook.fire("client_urgent_hint_changed", self)
                elif focus_behavior == "never":
                    logger.debug("Ignoring focus request (focus_on_window_activation='never')")
                else:
                    logger.debug(
                        "Invalid value for focus_on_window_activation: %s", focus_behavior
                    )
        elif atoms["_NET_CLOSE_WINDOW"] == opcode:
            self.kill()
        elif atoms["WM_CHANGE_STATE"] == opcode:
            state = data.data32[0]
            if state == NormalState:
                self.minimized = False
            elif state == IconicState and self.qtile.config.auto_minimize:
                self.minimized = True
        elif atoms["_NET_WM_DESKTOP"] == opcode:
            group_index = data.data32[0]
            try:
                group = self.qtile.groups[group_index]
                self.togroup(group.name)
            except (IndexError, TypeError):
                logger.warning("Unexpected _NET_WM_DESKTOP value received: %s", group_index)
        else:
            logger.debug("Unhandled client message: %s", atoms.get_name(opcode))

    def handle_PropertyNotify(self, e):  # noqa: N802
        name = self.qtile.core.conn.atoms.get_name(e.atom)
        if name == "WM_TRANSIENT_FOR":
            pass
        elif name == "WM_CLASS":
            self.update_wm_class()
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
        else:
            logger.debug("Unknown window property: %s", name)
        return False

    def _items(self, name: str) -> ItemT:
        if name == "group":
            return True, []
        if name == "layout":
            if self.group:
                return True, list(range(len(self.group.layouts)))
            return None
        if name == "screen":
            if self.group and self.group.screen:
                return True, []
        return None

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

    @expose_command()
    def move_floating(self, dx, dy):
        """Move window by dx and dy"""
        self.tweak_float(dx=dx, dy=dy)

    @expose_command()
    def resize_floating(self, dw, dh):
        """Add dw and dh to size of window"""
        self.tweak_float(dw=dw, dh=dh)

    @expose_command()
    def set_position_floating(self, x, y):
        """Move window to x and y"""
        self.tweak_float(x=x, y=y)

    @expose_command()
    def set_size_floating(self, w, h):
        """Set window dimensions to w and h"""
        self.tweak_float(w=w, h=h)

    @expose_command()
    def enable_floating(self):
        self.floating = True

    @expose_command()
    def disable_floating(self):
        self.floating = False

    @expose_command()
    def toggle_maximize(self):
        self.maximized = not self.maximized

    @expose_command()
    def toggle_fullscreen(self):
        self.fullscreen = not self.fullscreen

    @expose_command()
    def enable_fullscreen(self):
        self.fullscreen = True

    @expose_command()
    def disable_fullscreen(self):
        self.fullscreen = False

    def _is_in_window(self, x, y, window):
        return window.edges[0] <= x <= window.edges[2] and window.edges[1] <= y <= window.edges[3]

    @expose_command()
    def set_position(self, x, y):
        if self.floating:
            self.tweak_float(x, y)
            return
        curx, cury = self.qtile.core.get_mouse_position()
        for window in self.group.windows:
            if window == self or window.floating:
                continue
            if self._is_in_window(curx, cury, window):
                self.group.layout.swap(self, window)
                return

    @expose_command
    def focus(self, warp: bool = True) -> None:
        """Focus the window."""
        _Window.focus(self, warp)

        # Focusing a fullscreen window puts it into a different layer
        # priority group. If it's not there already, we need to move it.
        if self.fullscreen and not self.previous_layer[4]:
            self.change_layer()
