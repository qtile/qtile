# Copyright (c) 2009-2010 Aldo Cortesi
# Copyright (c) 2010 matt
# Copyright (c) 2010, 2012, 2014 dequis
# Copyright (c) 2010 Philip Kranz
# Copyright (c) 2010-2011 Paul Colomiets
# Copyright (c) 2011 osebelin
# Copyright (c) 2011 Mounier Florian
# Copyright (c) 2011 Kenji_Takahashi
# Copyright (c) 2011 Tzbob
# Copyright (c) 2012, 2014 roger
# Copyright (c) 2012, 2014-2015 Tycho Andersen
# Copyright (c) 2013 Tao Sauvage
# Copyright (c) 2014-2015 Sean Vig
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

"""
    A minimal EWMH-aware OO layer over xcffib. This is NOT intended to be
    complete - it only implements the subset of functionalty needed by qtile.
"""
import array
import contextlib
import functools
import inspect
import operator
import traceback
import typing
from collections import OrderedDict
from itertools import chain, islice, repeat

import cairocffi
import cairocffi.pixbuf
import cairocffi.xcb
import xcffib
import xcffib.randr
import xcffib.xinerama
import xcffib.xproto
from xcffib.xfixes import SelectionEventMask
from xcffib.xproto import CW, EventMask, SetMode, StackMode, WindowClass

from libqtile import hook, utils, xkeysyms
from libqtile.backend import base
from libqtile.backend.base.window import FloatStates
from libqtile.backend.x11.xcursors import Cursors
from libqtile.command.base import CommandError, CommandObject
from libqtile.log_utils import logger
from libqtile.utils import hex

keysyms = xkeysyms.keysyms


class XCBQError(Exception):
    pass


def rdict(d):
    r = {}
    for k, v in d.items():
        r.setdefault(v, []).append(k)
    return r


rkeysyms = rdict(xkeysyms.keysyms)

# Keyboard modifiers bitmask values from X Protocol
ModMasks = OrderedDict((
    ("shift", 1 << 0),
    ("lock", 1 << 1),
    ("control", 1 << 2),
    ("mod1", 1 << 3),
    ("mod2", 1 << 4),
    ("mod3", 1 << 5),
    ("mod4", 1 << 6),
    ("mod5", 1 << 7),
))

AllButtonsMask = 0b11111 << 8
ButtonMotionMask = 1 << 13
ButtonReleaseMask = 1 << 3

NormalHintsFlags = {
    "USPosition": 1,     # User-specified x, y
    "USSize": 2,         # User-specified width, height
    "PPosition": 4,      # Program-specified position
    "PSize": 8,          # Program-specified size
    "PMinSize": 16,      # Program-specified minimum size
    "PMaxSize": 32,      # Program-specified maximum size
    "PResizeInc": 64,    # Program-specified resize increments
    "PAspect": 128,      # Program-specified min and max aspect ratios
    "PBaseSize": 256,    # Program-specified base size
    "PWinGravity": 512,  # Program-specified window gravity
}

HintsFlags = {
    "InputHint": 1,          # input
    "StateHint": 2,          # initial_state
    "IconPixmapHint": 4,     # icon_pixmap
    "IconWindowHint": 8,     # icon_window
    "IconPositionHint": 16,  # icon_x & icon_y
    "IconMaskHint": 32,      # icon_mask
    "WindowGroupHint": 64,   # window_group
    "MessageHint": 128,      # (this bit is obsolete)
    "UrgencyHint": 256,      # urgency
}

# http://standards.freedesktop.org/wm-spec/latest/ar01s05.html#idm139870830002400
WindowTypes = {
    '_NET_WM_WINDOW_TYPE_DESKTOP': "desktop",
    '_NET_WM_WINDOW_TYPE_DOCK': "dock",
    '_NET_WM_WINDOW_TYPE_TOOLBAR': "toolbar",
    '_NET_WM_WINDOW_TYPE_MENU': "menu",
    '_NET_WM_WINDOW_TYPE_UTILITY': "utility",
    '_NET_WM_WINDOW_TYPE_SPLASH': "splash",
    '_NET_WM_WINDOW_TYPE_DIALOG': "dialog",
    '_NET_WM_WINDOW_TYPE_DROPDOWN_MENU': "dropdown",
    '_NET_WM_WINDOW_TYPE_POPUP_MENU': "menu",
    '_NET_WM_WINDOW_TYPE_TOOLTIP': "tooltip",
    '_NET_WM_WINDOW_TYPE_NOTIFICATION': "notification",
    '_NET_WM_WINDOW_TYPE_COMBO': "combo",
    '_NET_WM_WINDOW_TYPE_DND': "dnd",
    '_NET_WM_WINDOW_TYPE_NORMAL': "normal",
}

# http://standards.freedesktop.org/wm-spec/latest/ar01s05.html#idm139870829988448
net_wm_states = (
    '_NET_WM_STATE_MODAL',
    '_NET_WM_STATE_STICKY',
    '_NET_WM_STATE_MAXIMIZED_VERT',
    '_NET_WM_STATE_MAXIMIZED_HORZ',
    '_NET_WM_STATE_SHADED',
    '_NET_WM_STATE_SKIP_TASKBAR',
    '_NET_WM_STATE_SKIP_PAGER',
    '_NET_WM_STATE_HIDDEN',
    '_NET_WM_STATE_FULLSCREEN',
    '_NET_WM_STATE_ABOVE',
    '_NET_WM_STATE_BELOW',
    '_NET_WM_STATE_DEMANDS_ATTENTION',
    '_NET_WM_STATE_FOCUSED',
)

WindowStates = {
    None: 'normal',
    '_NET_WM_STATE_FULLSCREEN': 'fullscreen',
    '_NET_WM_STATE_DEMANDS_ATTENTION': 'urgent'
}

# Maps property names to types and formats.
PropertyMap = {
    # ewmh properties
    "_NET_DESKTOP_GEOMETRY": ("CARDINAL", 32),
    "_NET_SUPPORTED": ("ATOM", 32),
    "_NET_SUPPORTING_WM_CHECK": ("WINDOW", 32),
    "_NET_WM_NAME": ("UTF8_STRING", 8),
    "_NET_WM_PID": ("CARDINAL", 32),
    "_NET_CLIENT_LIST": ("WINDOW", 32),
    "_NET_CLIENT_LIST_STACKING": ("WINDOW", 32),
    "_NET_NUMBER_OF_DESKTOPS": ("CARDINAL", 32),
    "_NET_CURRENT_DESKTOP": ("CARDINAL", 32),
    "_NET_DESKTOP_NAMES": ("UTF8_STRING", 8),
    "_NET_WORKAREA": ("CARDINAL", 32),
    "_NET_ACTIVE_WINDOW": ("WINDOW", 32),
    "_NET_WM_DESKTOP": ("CARDINAL", 32),
    "_NET_WM_STRUT": ("CARDINAL", 32),
    "_NET_WM_STRUT_PARTIAL": ("CARDINAL", 32),
    "_NET_WM_WINDOW_OPACITY": ("CARDINAL", 32),
    "_NET_WM_WINDOW_TYPE": ("CARDINAL", 32),
    # Net State
    "_NET_WM_STATE": ("ATOM", 32),
    # Xembed
    "_XEMBED_INFO": ("_XEMBED_INFO", 32),
    # ICCCM
    "WM_STATE": ("WM_STATE", 32),
    # Qtile-specific properties
    "QTILE_INTERNAL": ("CARDINAL", 32)
}
for _name in net_wm_states:
    PropertyMap[_name] = ('ATOM', 32)

# TODO add everything required here:
# http://standards.freedesktop.org/wm-spec/latest/ar01s03.html
SUPPORTED_ATOMS = [
    # From http://standards.freedesktop.org/wm-spec/latest/ar01s03.html
    '_NET_SUPPORTED',
    '_NET_CLIENT_LIST',
    '_NET_CLIENT_LIST_STACKING',
    '_NET_CURRENT_DESKTOP',
    '_NET_ACTIVE_WINDOW',
    '_NET_SUPPORTING_WM_CHECK',
    # From http://standards.freedesktop.org/wm-spec/latest/ar01s05.html
    '_NET_WM_NAME',
    '_NET_WM_VISIBLE_NAME',
    '_NET_WM_ICON_NAME',
    '_NET_WM_DESKTOP',
    '_NET_WM_WINDOW_TYPE',
    '_NET_WM_STATE',
    '_NET_WM_STRUT',
    '_NET_WM_STRUT_PARTIAL',
    '_NET_WM_PID',
]
SUPPORTED_ATOMS.extend(WindowTypes.keys())
SUPPORTED_ATOMS.extend(net_wm_states)

XCB_CONN_ERRORS = {
    1: 'XCB_CONN_ERROR',
    2: 'XCB_CONN_CLOSED_EXT_NOTSUPPORTED',
    3: 'XCB_CONN_CLOSED_MEM_INSUFFICIENT',
    4: 'XCB_CONN_CLOSED_REQ_LEN_EXCEED',
    5: 'XCB_CONN_CLOSED_PARSE_ERR',
    6: 'XCB_CONN_CLOSED_INVALID_SCREEN',
    7: 'XCB_CONN_CLOSED_FDPASSING_FAILED',
}


class MaskMap:
    """
        A general utility class that encapsulates the way the bitmask/listofvalue idiom
        works in X protocol. It understands a special attribute _maskvalue on
        objects, which will be used instead of the object value if present.
        This lets us pass in a Font object, rather than Font.fid, for example.
    """
    def __init__(self, obj):
        self.mmap = []
        for i in dir(obj):
            if not i.startswith("_"):
                self.mmap.append((getattr(obj, i), i.lower()))
        self.mmap.sort()

    def __call__(self, **kwargs):
        """
            kwargs: keys should be in the mmap name set

            Returns a (mask, values) tuple.
        """
        mask = 0
        values = []
        for m, s in self.mmap:
            if s in kwargs:
                val = kwargs.get(s)
                if val is not None:
                    mask |= m
                    values.append(getattr(val, "_maskvalue", val))
                del kwargs[s]
        if kwargs:
            raise ValueError("Unknown mask names: %s" % list(kwargs.keys()))
        return mask, values


ConfigureMasks = MaskMap(xcffib.xproto.ConfigWindow)
AttributeMasks = MaskMap(CW)


class AtomCache:
    def __init__(self, conn):
        self.conn = conn
        self.atoms = {}
        self.reverse = {}

        # We can change the pre-loads not to wait for a return
        for name in WindowTypes.keys():
            self.insert(name=name)

        for i in dir(xcffib.xproto.Atom):
            if not i.startswith("_"):
                self.insert(name=i, atom=getattr(xcffib.xproto.Atom, i))

    def insert(self, name=None, atom=None):
        assert name or atom
        if atom is None:
            c = self.conn.conn.core.InternAtom(False, len(name), name)
            atom = c.reply().atom
        if name is None:
            c = self.conn.conn.core.GetAtomName(atom)
            name = c.reply().name.to_string()
        self.atoms[name] = atom
        self.reverse[atom] = name

    def get_name(self, atom):
        if atom not in self.reverse:
            self.insert(atom=atom)
        return self.reverse[atom]

    def __getitem__(self, key):
        if key not in self.atoms:
            self.insert(name=key)
        return self.atoms[key]


class _Wrapper:
    def __init__(self, wrapped):
        self.wrapped = wrapped

    def __getattr__(self, x):
        return getattr(self.wrapped, x)


class Screen(_Wrapper):
    """
        This represents an actual X screen.
    """
    def __init__(self, conn, screen):
        _Wrapper.__init__(self, screen)
        self.default_colormap = Colormap(conn, screen.default_colormap)
        self.root = XWindow(conn, self.root)


class PseudoScreen:
    """
        This may be a Xinerama screen or a RandR CRTC, both of which are
        rectangular sections of an actual Screen.
    """
    def __init__(self, conn, x, y, width, height):
        self.conn = conn
        self.x = x
        self.y = y
        self.width = width
        self.height = height


class Colormap:
    def __init__(self, conn, cid):
        self.conn = conn
        self.cid = cid

    def alloc_color(self, color):
        """
            Flexible color allocation.
        """
        try:
            return self.conn.conn.core.AllocNamedColor(
                self.cid, len(color), color
            ).reply()
        except xcffib.xproto.NameError:

            def x8to16(i):
                return 0xffff * (i & 0xff) // 0xff

            color = hex(color)
            r = x8to16(int(color[-6] + color[-5], 16))
            g = x8to16(int(color[-4] + color[-3], 16))
            b = x8to16(int(color[-2] + color[-1], 16))
            return self.conn.conn.core.AllocColor(self.cid, r, g, b).reply()


class Xinerama:
    def __init__(self, conn):
        self.ext = conn.conn(xcffib.xinerama.key)

    def query_screens(self):
        r = self.ext.QueryScreens().reply()
        return r.screen_info


class RandR:
    def __init__(self, conn):
        self.ext = conn.conn(xcffib.randr.key)
        self.ext.SelectInput(
            conn.default_screen.root.wid,
            xcffib.randr.NotifyMask.ScreenChange
        )

    def query_crtcs(self, root):
        crtc_list = []
        for crtc in self.ext.GetScreenResources(root).reply().crtcs:
            crtc_info = self.ext.GetCrtcInfo(crtc, xcffib.CurrentTime).reply()
            crtc_dict = {
                "x": crtc_info.x,
                "y": crtc_info.y,
                "width": crtc_info.width,
                "height": crtc_info.height,
            }
            crtc_list.append(crtc_dict)
        return crtc_list


class XFixes:
    selection_mask = SelectionEventMask.SetSelectionOwner | \
        SelectionEventMask.SelectionClientClose | \
        SelectionEventMask.SelectionWindowDestroy

    def __init__(self, conn):
        self.conn = conn
        self.ext = conn.conn(xcffib.xfixes.key)
        self.ext.QueryVersion(xcffib.xfixes.MAJOR_VERSION,
                              xcffib.xfixes.MINOR_VERSION)

    def select_selection_input(self, window, selection="PRIMARY"):
        _selection = self.conn.atoms[selection]
        self.conn.xfixes.ext.SelectSelectionInput(window.wid,
                                                  _selection,
                                                  self.selection_mask)


class NetWmState:
    """NetWmState is a descriptor for _NET_WM_STATE_* properties"""
    def __init__(self, prop_name):
        self.prop_name = prop_name

    def __get__(self, xcbq_win, cls):
        try:
            atom = self.atom
        except AttributeError:
            atom = xcbq_win.conn.atoms[self.prop_name]
            self.atom = atom
        reply = xcbq_win.get_property('_NET_WM_STATE', 'ATOM', unpack=int)
        if atom in reply:
            return True
        return False

    def __set__(self, xcbq_win, value):
        try:
            atom = self.atom
        except AttributeError:
            atom = xcbq_win.conn.atoms[self.prop_name]
            self.atom = atom

        value = bool(value)
        reply = list(xcbq_win.get_property('_NET_WM_STATE', 'ATOM', unpack=int))
        is_set = atom in reply
        if is_set and not value:
            reply.remove(atom)
            xcbq_win.set_property('_NET_WM_STATE', reply)
        elif value and not is_set:
            reply.append(atom)
            xcbq_win.set_property('_NET_WM_STATE', reply)
        return


class XWindow(base.Window):
    def __init__(self, conn, wid):
        self.conn = conn
        self.wid = wid

    def _property_string(self, r):
        """Extract a string from a window property reply message"""
        return r.value.to_string()

    def _property_utf8(self, r):
        return r.value.to_utf8()

    def send_event(self, synthevent, mask=EventMask.NoEvent):
        self.conn.conn.core.SendEvent(False, self.wid, mask, synthevent.pack())

    def kill_client(self):
        self.conn.conn.core.KillClient(self.wid)

    def set_input_focus(self):
        self.conn.conn.core.SetInputFocus(
            xcffib.xproto.InputFocus.PointerRoot,
            self.wid,
            xcffib.xproto.Time.CurrentTime
        )

    def warp_pointer(self, x, y):
        """Warps the pointer to the location `x`, `y` on the window"""
        self.conn.conn.core.WarpPointer(
            0, self.wid,  # src_window, dst_window
            0, 0,         # src_x, src_y
            0, 0,         # src_width, src_height
            x, y          # dest_x, dest_y
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

        r = self.get_property(
            xcffib.xproto.Atom.WM_NAME,
            xcffib.xproto.GetPropertyType.Any
        )
        if r:
            return self._property_string(r)

    def get_wm_hints(self):
        wm_hints = self.get_property("WM_HINTS", xcffib.xproto.GetPropertyType.Any)
        if wm_hints:
            atoms_list = wm_hints.value.to_atoms()
            flags = {k for k, v in HintsFlags.items() if atoms_list[0] & v}
            return {
                "flags": flags,
                "input": atoms_list[1] if "InputHint" in flags else None,
                "initial_state": atoms_list[2] if "StateHing" in flags else None,
                "icon_pixmap": atoms_list[3] if "IconPixmapHint" in flags else None,
                "icon_window": atoms_list[4] if "IconWindowHint" in flags else None,
                "icon_x": atoms_list[5] if "IconPositionHint" in flags else None,
                "icon_y": atoms_list[6] if "IconPositionHint" in flags else None,
                "icon_mask": atoms_list[7] if "IconMaskHint" in flags else None,
                "window_group": atoms_list[8] if 'WindowGroupHint' in flags else None,
            }

    def get_wm_normal_hints(self):
        wm_normal_hints = self.get_property(
            "WM_NORMAL_HINTS",
            xcffib.xproto.GetPropertyType.Any
        )
        if wm_normal_hints:
            atom_list = wm_normal_hints.value.to_atoms()
            flags = {k for k, v in NormalHintsFlags.items() if atom_list[0] & v}
            hints = {
                "flags": flags,
                "min_width": atom_list[5],
                "min_height": atom_list[6],
                "max_width": atom_list[7],
                "max_height": atom_list[8],
                "width_inc": atom_list[9],
                "height_inc": atom_list[10],
                "min_aspect": (atom_list[11], atom_list[12]),
                "max_aspect": (atom_list[13], atom_list[14])
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
        """Return an (instance, class) tuple if WM_CLASS exists, or None"""
        r = self.get_property("WM_CLASS", "STRING")
        if r:
            s = self._property_string(r)
            return tuple(s.strip("\0").split("\0"))
        return tuple()

    def get_wm_window_role(self):
        r = self.get_property("WM_WINDOW_ROLE", "STRING")
        if r:
            return self._property_string(r)

    def get_wm_transient_for(self):
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
        r = self.get_property('_NET_WM_WINDOW_TYPE', "ATOM", unpack=int)
        if r:
            name = self.conn.atoms.get_name(r[0])
            return WindowTypes.get(name, name)

    def get_net_wm_state(self):
        r = self.get_property('_NET_WM_STATE', "ATOM", unpack=int)
        if r:
            names = [self.conn.atoms.get_name(p) for p in r]
            return [WindowStates.get(n, n) for n in names]
        return []

    def get_net_wm_pid(self):
        r = self.get_property("_NET_WM_PID", unpack=int)
        if r:
            return r[0]

    def configure(self, **kwargs):
        """
        Arguments can be: x, y, width, height, border, sibling, stackmode
        """
        mask, values = ConfigureMasks(**kwargs)
        # older versions of xcb pack everything into unsigned ints "=I"
        # since 1.12, uses switches to pack things sensibly
        if float(".".join(xcffib.__xcb_proto_version__.split(".")[0: 2])) < 1.12:
            values = [i & 0xffffffff for i in values]
        return self.conn.conn.core.ConfigureWindow(self.wid, mask, values)

    def set_attribute(self, **kwargs):
        mask, values = AttributeMasks(**kwargs)
        self.conn.conn.core.ChangeWindowAttributesChecked(
            self.wid, mask, values
        )

    def set_cursor(self, name):
        cursor_id = self.conn.cursors[name]
        mask, values = AttributeMasks(cursor=cursor_id)
        self.conn.conn.core.ChangeWindowAttributesChecked(
            self.wid, mask, values
        )

    def set_property(self, name, value, type=None, format=None):
        """
        Parameters
        ==========
        name : String Atom name
        type : String Atom name
        format : 8, 16, 32
        """
        if name in PropertyMap:
            if type or format:
                raise ValueError(
                    "Over-riding default type or format for property."
                )
            type, format = PropertyMap[name]
        else:
            if None in (type, format):
                raise ValueError(
                    "Must specify type and format for unknown property."
                )

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
                value
            ).check()
        except xcffib.xproto.WindowError:
            logger.debug(
                'X error in SetProperty (wid=%r, prop=%r), ignoring',
                self.wid, name)

    def get_property(self, prop, type=None, unpack=None):
        """Return the contents of a property as a GetPropertyReply

        If unpack is specified, a tuple of values is returned.  The type to
        unpack, either `str` or `int` must be specified.
        """
        if type is None:
            if prop not in PropertyMap:
                raise ValueError(
                    "Must specify type for unknown property."
                )
            else:
                type, _ = PropertyMap[prop]

        try:
            r = self.conn.conn.core.GetProperty(
                False, self.wid,
                self.conn.atoms[prop]
                if isinstance(prop, str)
                else prop,
                self.conn.atoms[type]
                if isinstance(type, str)
                else type,
                0, (2 ** 32) - 1
            ).reply()
        except (xcffib.xproto.WindowError, xcffib.xproto.AccessError):
            logger.debug(
                'X error in GetProperty (wid=%r, prop=%r), ignoring',
                self.wid, prop)
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

    def paint_borders(self, color):
        if color:
            self.set_attribute(borderpixel=self.conn.color_pixel(color))


class Connection:
    _extmap = {
        "xinerama": Xinerama,
        "randr": RandR,
        "xfixes": XFixes,
    }

    def __init__(self, display):
        self.conn = xcffib.connect(display=display)
        self._connected = True
        self.cursors = Cursors(self)
        self.setup = self.conn.get_setup()
        extensions = self.extensions()
        self.screens = [Screen(self, i) for i in self.setup.roots]
        self.default_screen = self.screens[self.conn.pref_screen]

        for i in extensions:
            if i in self._extmap:
                setattr(self, i, self._extmap[i](self))

        self.pseudoscreens = []
        if "xinerama" in extensions:
            for i, s in enumerate(self.xinerama.query_screens()):
                scr = PseudoScreen(
                    self,
                    s.x_org,
                    s.y_org,
                    s.width,
                    s.height,
                )
                self.pseudoscreens.append(scr)
        elif "randr" in extensions:
            for i in self.randr.query_crtcs(self.screens[0].root.wid):
                scr = PseudoScreen(
                    self,
                    i["x"],
                    i["y"],
                    i["width"],
                    i["height"],
                )
                self.pseudoscreens.append(scr)

        self.atoms = AtomCache(self)

        self.code_to_syms = {}
        self.sym_to_codes = None
        self.refresh_keymap()

        self.modmap = None
        self.refresh_modmap()

    def finalize(self):
        self.cursors.finalize()
        self.disconnect()

    def refresh_keymap(self, first=None, count=None):
        if first is None:
            first = self.setup.min_keycode
            count = self.setup.max_keycode - self.setup.min_keycode + 1
        q = self.conn.core.GetKeyboardMapping(first, count).reply()

        assert len(q.keysyms) % q.keysyms_per_keycode == 0
        for i in range(len(q.keysyms) // q.keysyms_per_keycode):
            self.code_to_syms[first + i] = \
                q.keysyms[i * q.keysyms_per_keycode:(i + 1) * q.keysyms_per_keycode]

        sym_to_codes = {}
        for k, s in self.code_to_syms.items():
            for sym in s:
                if sym == 0:
                    continue
                if sym not in sym_to_codes:
                    sym_to_codes[sym] = [k]
                elif k not in sym_to_codes[sym]:
                    sym_to_codes[sym].append(k)

        self.sym_to_codes = sym_to_codes

    def refresh_modmap(self):
        reply = self.conn.core.GetModifierMapping().reply()
        modmap = {}
        names = (repeat(name, reply.keycodes_per_modifier) for name in ModMasks)
        for name, keycode in zip(chain.from_iterable(names), reply.keycodes):
            value = modmap.setdefault(name, [])
            value.append(keycode)
        self.modmap = modmap

    def get_modifier(self, keycode):
        """Return the modifier matching keycode"""
        for n, l in self.modmap.items():
            if keycode in l:
                return n
        return None

    def keysym_to_keycode(self, keysym):
        return self.sym_to_codes.get(keysym, [0])

    def keycode_to_keysym(self, keycode, modifier):
        if keycode >= len(self.code_to_syms) or \
                modifier >= len(self.code_to_syms[keycode]):
            return 0
        return self.code_to_syms[keycode][modifier]

    def create_window(self, x, y, width, height):
        wid = self.conn.generate_id()
        self.conn.core.CreateWindow(
            self.default_screen.root_depth,
            wid,
            self.default_screen.root.wid,
            x, y, width, height, 0,
            WindowClass.InputOutput,
            self.default_screen.root_visual,
            CW.BackPixel | CW.EventMask,
            [
                self.default_screen.black_pixel,
                EventMask.StructureNotify | EventMask.Exposure
            ]
        )
        return XWindow(self, wid)

    def disconnect(self):
        try:
            self.conn.disconnect()
        except xcffib.ConnectionException:
            logger.error("Failed to disconnect, connection already failed?")
        self._connected = False

    def flush(self):
        if self._connected:
            return self.conn.flush()

    def xsync(self):
        # The idea here is that pushing an innocuous request through the queue
        # and waiting for a response "syncs" the connection, since requests are
        # serviced in order.
        self.conn.core.GetInputFocus().reply()

    def get_setup(self):
        return self.conn.get_setup()

    def extensions(self):
        return set(
            i.name.to_string().lower()
            for i in self.conn.core.ListExtensions().reply().names
        )

    def fixup_focus(self):
        """
        If the X11 focus is set to None, all keypress events are discarded,
        which makes our hotkeys not work. This fixes up the focus so it is not
        None.
        """
        window = self.conn.core.GetInputFocus().reply().focus
        if window == xcffib.xproto.InputFocus._None:
            self.conn.core.SetInputFocus(
                xcffib.xproto.InputFocus.PointerRoot,
                xcffib.xproto.InputFocus.PointerRoot,
                xcffib.xproto.Time.CurrentTime,
            )

    @functools.lru_cache()
    def color_pixel(self, name):
        pixel = self.screens[0].default_colormap.alloc_color(name).pixel
        return pixel | 0xff << 24


class Painter:
    def __init__(self, display):
        self.conn = xcffib.connect(display=display)
        self.setup = self.conn.get_setup()
        self.screens = [Screen(self, i) for i in self.setup.roots]
        self.default_screen = self.screens[self.conn.pref_screen]
        self.conn.core.SetCloseDownMode(xcffib.xproto.CloseDown.RetainPermanent)
        self.atoms = AtomCache(self)

    def paint(self, screen, image_path, mode=None):
        try:
            with open(image_path, 'rb') as f:
                image, _ = cairocffi.pixbuf.decode_to_image_surface(f.read())
        except IOError as e:
            logger.error('Wallpaper: %s' % e)
            return

        root_pixmap = self.default_screen.root.get_property(
            '_XROOTPMAP_ID', xcffib.xproto.Atom.PIXMAP, int
        )
        if not root_pixmap:
            root_pixmap = self.default_screen.root.get_property(
                'ESETROOT_PMAP_ID', xcffib.xproto.Atom.PIXMAP, int
            )
        if root_pixmap:
            root_pixmap = root_pixmap[0]
        else:
            root_pixmap = self.conn.generate_id()
            self.conn.core.CreatePixmap(
                self.default_screen.root_depth,
                root_pixmap,
                self.default_screen.root.wid,
                self.default_screen.width_in_pixels,
                self.default_screen.height_in_pixels,
            )

        for depth in self.default_screen.allowed_depths:
            for visual in depth.visuals:
                if visual.visual_id == self.default_screen.root_visual:
                    root_visual = visual
                    break
        surface = cairocffi.xcb.XCBSurface(
            self.conn, root_pixmap, root_visual,
            self.default_screen.width_in_pixels,
            self.default_screen.height_in_pixels,
        )

        context = cairocffi.Context(surface)
        with context:
            context.translate(screen.x, screen.y)
            if mode == 'fill':
                context.rectangle(0, 0, screen.width, screen.height)
                context.clip()
                image_w = image.get_width()
                image_h = image.get_height()
                width_ratio = screen.width / image_w
                if width_ratio * image_h >= screen.height:
                    context.scale(width_ratio)
                else:
                    height_ratio = screen.height / image_h
                    context.translate(
                        - (image_w * height_ratio - screen.width) // 2, 0
                    )
                    context.scale(height_ratio)
            elif mode == 'stretch':
                context.scale(
                    sx=screen.width / image.get_width(),
                    sy=screen.height / image.get_height(),
                )
            context.set_source_surface(image)
            context.paint()

        self.conn.core.ChangeProperty(
            xcffib.xproto.PropMode.Replace,
            self.default_screen.root.wid,
            self.atoms['_XROOTPMAP_ID'],
            xcffib.xproto.Atom.PIXMAP,
            32, 1, [root_pixmap]
        )
        self.conn.core.ChangeProperty(
            xcffib.xproto.PropMode.Replace,
            self.default_screen.root.wid,
            self.atoms['ESETROOT_PMAP_ID'],
            xcffib.xproto.Atom.PIXMAP,
            32, 1, [root_pixmap]
        )
        self.conn.core.ChangeWindowAttributes(
            self.default_screen.root.wid,
            xcffib.xproto.CW.BackPixmap, [root_pixmap]
        )
        self.conn.core.ClearArea(
            0, self.default_screen.root.wid, 0, 0,
            self.default_screen.width_in_pixels,
            self.default_screen.height_in_pixels
        )
        self.conn.flush()

    def __del__(self):
        self.conn.disconnect()


def get_keysym(key: str) -> int:
    keysym = keysyms.get(key)
    if not keysym:
        raise XCBQError("Unknown key: %s" % key)
    return keysym


def translate_modifiers(mask: int) -> typing.List[str]:
    r = []
    for k, v in ModMasks.items():
        if mask & v:
            r.append(k)
    return r


def translate_masks(modifiers: typing.List[str]) -> int:
    """
    Translate a modifier mask specified as a list of strings into an or-ed
    bit representation.
    """
    masks = []
    for i in modifiers:
        try:
            masks.append(ModMasks[i])
        except KeyError as e:
            raise XCBQError("Unknown modifier: %s" % i) from e
    if masks:
        return functools.reduce(operator.or_, masks)
    else:
        return 0


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
        self._float_state = FloatStates.NOT_FLOATING
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

        # FIXME
        # h values
        # {
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
        # }

        if normh:
            normh['min_width'] = max(0, normh.get('min_width', 0))
            normh['min_height'] = max(0, normh.get('min_height', 0))
            if not normh['base_width'] and \
                    normh['min_width'] and \
                    normh['width_inc']:
                # seems xcffib does ignore base width :(
                normh['base_width'] = (
                    normh['min_width'] % normh['width_inc']
                )
            if not normh['base_height'] and \
                    normh['min_height'] and \
                    normh['height_inc']:
                # seems xcffib does ignore base height :(
                normh['base_height'] = (
                    normh['min_height'] % normh['height_inc']
                )
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
            floating=self._float_state != FloatStates.NOT_FLOATING,
            float_info=self._float_info,
            maximized=self._float_state == FloatStates.MAXIMIZED,
            minimized=self._float_state == FloatStates.MINIMIZED,
            fullscreen=self._float_state == FloatStates.FULLSCREEN
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


class Internal(base.Internal, _Window):
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


class Static(base.Static, _Window):
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
        return self._float_state != FloatStates.NOT_FLOATING

    @floating.setter
    def floating(self, do_float):
        if do_float and self._float_state == FloatStates.NOT_FLOATING:
            if self.group and self.group.screen:
                screen = self.group.screen
                self._enablefloating(
                    screen.x + self.float_x, screen.y + self.float_y, self.float_width, self.float_height
                )
            else:
                # if we are setting floating early, e.g. from a hook, we don't have a screen yet
                self._float_state = FloatStates.FLOATING
        elif (not do_float) and self._float_state != FloatStates.NOT_FLOATING:
            if self._float_state == FloatStates.FLOATING:
                # store last size
                self.float_width = self.width
                self.float_height = self.height
            self._float_state = FloatStates.NOT_FLOATING
            self.group.mark_floating(self, False)
            hook.fire('float_change')

    def toggle_floating(self):
        self.floating = not self.floating

    @property
    def fullscreen(self):
        return self._float_state == FloatStates.FULLSCREEN

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
                new_float_state=FloatStates.FULLSCREEN
            )
            set_state(prev_state, prev_state | atom)
            return

        if self._float_state == FloatStates.FULLSCREEN:
            # The order of calling set_state() and then
            # setting self.floating = False is important
            set_state(prev_state, prev_state - atom)
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
            screen = self.group.screen or \
                self.qtile.find_closest_screen(self.x, self.y)

            self._enablefloating(
                screen.dx,
                screen.dy,
                screen.dwidth,
                screen.dheight,
                new_float_state=FloatStates.MAXIMIZED
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

    def _reconfigure_floating(self, new_float_state=FloatStates.FLOATING):
        if new_float_state == FloatStates.MINIMIZED:
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
                if new_float_state == FloatStates.FULLSCREEN:
                    self.x += int(width_adjustment / 2)

            if self.hints['base_height'] and self.hints['height_inc']:
                height_adjustment = (height - self.hints['base_height']) % self.hints['height_inc']
                height -= height_adjustment
                if new_float_state == FloatStates.FULLSCREEN:
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
                        new_float_state=FloatStates.FLOATING):
        if new_float_state != FloatStates.MINIMIZED:
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

    def cmd_set_position(self, dx, dy):
        if self.floating:
            self.tweak_float(dx, dy)
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
