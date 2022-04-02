from __future__ import annotations

import array
import contextlib
import inspect
import traceback
from itertools import islice
from typing import TYPE_CHECKING

import xcffib
import xcffib.xproto
from xcffib.wrappers import GContextID, PixmapID
from xcffib.xproto import EventMask, SetMode, StackMode

from libqtile import hook, utils
from libqtile.backend import base
from libqtile.backend.base import FloatStates
from libqtile.backend.x11 import xcbq
from libqtile.backend.x11.drawer import Drawer
from libqtile.command.base import CommandError
from libqtile.log_utils import logger

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
            name = self.conn.atoms.get_name(r[0])
            return xcbq.WindowTypes.get(name, name)

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
        q = self.conn.conn.core.QueryTree(self.wid).reply()
        root = None
        parent = None
        if q.root:
            root = XWindow(self.conn, q.root)
        if q.parent:
            parent = XWindow(self.conn, q.parent)
        return root, parent, [XWindow(self.conn, i) for i in q.children]

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
        self.hidden = True
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

        if self.qtile.config.auto_fullscreen:
            triggered.append("fullscreen")

        state = self.window.get_net_wm_state()

        for s in triggered:
            setattr(self, s, (s in state))

    @property
    def urgent(self):
        return self.hints["urgent"] or self._demands_attention

    @urgent.setter
    def urgent(self, val):
        self._demands_attention = val
        # TODO unset window hint as well?
        if not val:
            self.hints["urgent"] = False

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
        # Grab button 1 to focus upon click when unfocussed
        for amask in self.qtile.core._auto_modmasks():
            self.qtile.core.conn.conn.core.GrabButton(
                True,
                self.window.wid,
                EventMask.ButtonPress,
                xcffib.xproto.GrabMode.Sync,
                xcffib.xproto.GrabMode.Async,
                xcffib.xproto.Atom._None,
                xcffib.xproto.Atom._None,
                1,
                amask,
            )

    def _ungrab_click(self):
        # Ungrab button 1 when focussed
        self.qtile.core.conn.conn.core.UngrabButton(
            xcffib.xproto.Atom.Any,
            self.window.wid,
            xcffib.xproto.ModMask.Any,
        )

    def get_pid(self):
        return self.window.get_net_wm_pid()

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

        kwarg = dict(
            x=x,
            y=y,
            width=width,
            height=height,
        )
        if above:
            kwarg["stackmode"] = StackMode.Above

        self.window.configure(**kwarg)
        self.paint_borders(bordercolor, borderwidth)

        if send_notify:
            self.send_configure_notify(x, y, width, height)

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
        return self.window.get_wm_type() != "notification"

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

        # we didn't focus this time. but now the window knows if it wants
        # focus, it should SetFocus() itself; we'll get another notification
        # about this.
        return False

    def focus(self, warp: bool) -> None:
        did_focus = self._do_focus()
        if not did_focus:
            return
        if isinstance(self, base.Internal):
            # self._do_focus is enough for internal windows
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

        if self.group:
            self.group.current_window = self
        hook.fire("client_focus", self)

    def cmd_focus(self, warp: bool = True) -> None:
        """Focuses the window."""
        self.focus(warp)

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

    def create_drawer(self, width: int, height: int) -> base.Drawer:
        """Create a Drawer that draws to this window."""
        return Drawer(self.qtile, self, width, height)

    def kill(self):
        if self.window.wid in self.qtile.windows_map:
            # It will be present during config reloads; absent during shutdown as this
            # will follow graceful_shutdown
            self.qtile.core.conn.conn.core.DestroyWindow(self.window.wid)

    def cmd_kill(self):
        self.kill()

    def handle_Expose(self, e):  # noqa: N802
        self.process_window_expose()

    def handle_ButtonPress(self, e):  # noqa: N802
        self.process_button_click(e.event_x, e.event_y, e.detail)

    def handle_ButtonRelease(self, e):  # noqa: N802
        self.process_button_release(e.event_x, e.event_y, e.detail)

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
            self.screen.x + self.x,
            self.screen.y + self.y,
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

    def cmd_bring_to_front(self):
        self.window.configure(stackmode=StackMode.Above)


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
        if do_float and self._float_state == FloatStates.NOT_FLOATING:
            if self.group and self.group.screen:
                screen = self.group.screen
                self._enablefloating(
                    screen.x + self.float_x,
                    screen.y + self.float_y,
                    self._float_width,
                    self._float_height,
                )
            else:
                # if we are setting floating early, e.g. from a hook, we don't have a screen yet
                self._float_state = FloatStates.FLOATING
        elif (not do_float) and self._float_state != FloatStates.NOT_FLOATING:
            self.update_fullscreen_wm_state(False)
            if self._float_state == FloatStates.FLOATING:
                # store last size
                self._float_width = self.width
                self._float_height = self.height
            self._float_state = FloatStates.NOT_FLOATING
            self.group.mark_floating(self, False)
            hook.fire("float_change")

    @property
    def wants_to_fullscreen(self):
        try:
            return "fullscreen" in self.window.get_net_wm_state()
        except (xcffib.xproto.WindowError, xcffib.xproto.AccessError):
            pass
        return False

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
            screen = self.group.screen or self.qtile.find_closest_screen(self.x, self.y)

            bw = self.group.floating_layout.fullscreen_border_width
            self._enablefloating(
                screen.x,
                screen.y,
                screen.width - 2 * bw,
                screen.height - 2 * bw,
                new_float_state=FloatStates.FULLSCREEN,
            )
            return

        if self._float_state == FloatStates.FULLSCREEN:
            self.floating = False
            return

    def toggle_fullscreen(self):
        self.fullscreen = not self.fullscreen

    @property
    def maximized(self):
        return self._float_state == FloatStates.MAXIMIZED

    @maximized.setter
    def maximized(self, do_maximize):
        if do_maximize:
            screen = self.group.screen or self.qtile.find_closest_screen(self.x, self.y)

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
                self.floating = False

    def toggle_maximize(self, state=FloatStates.MAXIMIZED):
        self.maximized = not self.maximized

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

    def toggle_minimize(self):
        self.minimized = not self.minimized

    def cmd_static(
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
        self.qtile.core.update_client_list(self.qtile.windows_map)
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

    def getsize(self):
        return (self.width, self.height)

    def getposition(self):
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
                above=True,
                respect_hints=True,
            )
        if self._float_state != new_float_state:
            self._float_state = new_float_state
            if self.group:  # may be not, if it's called from hook
                self.group.mark_floating(self, True)
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
                raise CommandError("No such group: %s" % group_name)

        if self.group is group:
            if toggle and hasattr(self.group.screen, "previous_group"):
                group = self.group.screen.previous_group
            else:
                return

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
            group.cmd_toscreen(toggle=toggle)

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
            icons["%sx%s" % (width, height)] = arr
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
            else:  # XCB_EWMH_CLIENT_SOURCE_TYPE_OTHER
                focus_behavior = self.qtile.config.focus_on_window_activation
                if focus_behavior == "focus":
                    logger.debug("Focusing window")
                    self.qtile.current_screen.set_group(self.group)
                    self.group.focus(self)
                elif focus_behavior == "smart":
                    if not self.group.screen:
                        logger.debug("Ignoring focus request")
                        return
                    if self.group.screen == self.qtile.current_screen:
                        logger.debug("Focusing window")
                        self.qtile.current_screen.set_group(self.group)
                        self.group.focus(self)
                    else:  # self.group.screen != self.qtile.current_screen:
                        logger.debug("Setting urgent flag for window")
                        self.urgent = True
                elif focus_behavior == "urgent":
                    logger.debug("Setting urgent flag for window")
                    self.urgent = True
                elif focus_behavior == "never":
                    logger.debug("Ignoring focus request")
                else:
                    logger.debug(
                        "Invalid value for focus_on_window_activation: {}".format(focus_behavior)
                    )
        elif atoms["_NET_CLOSE_WINDOW"] == opcode:
            self.kill()
        elif atoms["WM_CHANGE_STATE"] == opcode:
            state = data.data32[0]
            if state == NormalState:
                self.minimized = False
            elif state == IconicState and self.qtile.config.auto_minimize:
                self.minimized = True
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

    def cmd_kill(self):
        """Kill this window

        Try to do this politely if the client support
        this, otherwise be brutal.
        """
        self.kill()

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

    def cmd_place(self, x, y, width, height, borderwidth, bordercolor, above=False, margin=None):
        self.place(x, y, width, height, borderwidth, bordercolor, above, margin)

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

    def _is_in_window(self, x, y, window):
        return window.edges[0] <= x <= window.edges[2] and window.edges[1] <= y <= window.edges[3]

    def cmd_set_position(self, x, y):
        if self.floating:
            self.tweak_float(x, y)
            return
        curx, cury = self.qtile.core.get_mouse_position()
        for window in self.group.windows:
            if window == self or window.floating:
                continue
            if self._is_in_window(curx, cury, window):
                clients = self.group.layout.clients
                index1 = clients.index(self)
                index2 = clients.index(window)
                clients[index1], clients[index2] = clients[index2], clients[index1]
                self.group.layout.focused = index2
                self.group.layout_all()
                break
