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
    A minimal EWMH-aware OO layer over xpyb. This is NOT intended to be
    complete - it only implements the subset of functionalty needed by qtile.
"""
from __future__ import print_function, division

import six

from xcffib.xproto import CW, WindowClass, EventMask
from xcffib.xfixes import SelectionEventMask

import xcffib
import xcffib.randr
import xcffib.xinerama
import xcffib.xproto

from . import xkeysyms
from .log_utils import logger
from .xcursors import Cursors

keysyms = xkeysyms.keysyms


def rdict(d):
    r = {}
    for k, v in d.items():
        r.setdefault(v, []).append(k)
    return r

rkeysyms = rdict(xkeysyms.keysyms)

# These should be in xpyb:
ModMasks = {
    "shift": 1 << 0,
    "lock": 1 << 1,
    "control": 1 << 2,
    "mod1": 1 << 3,
    "mod2": 1 << 4,
    "mod3": 1 << 5,
    "mod4": 1 << 6,
    "mod5": 1 << 7,
}
ModMapOrder = [
    "shift",
    "lock",
    "control",
    "mod1",
    "mod2",
    "mod3",
    "mod4",
    "mod5"
]

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
    "_NET_WM_STATE_STICKY": ("ATOM", 32),
    "_NET_WM_STATE_SKIP_TASKBAR": ("ATOM", 32),
    "_NET_WM_STATE_FULLSCREEN": ("ATOM", 32),
    "_NET_WM_STATE_MAXIMIZED_HORZ": ("ATOM", 32),
    "_NET_WM_STATE_MAXIMIZED_VERT": ("ATOM", 32),
    "_NET_WM_STATE_ABOVE": ("ATOM", 32),
    "_NET_WM_STATE_BELOW": ("ATOM", 32),
    "_NET_WM_STATE_MODAL": ("ATOM", 32),
    "_NET_WM_STATE_HIDDEN": ("ATOM", 32),
    "_NET_WM_STATE_DEMANDS_ATTENTION": ("ATOM", 32),
    # Xembed
    "_XEMBED_INFO": ("_XEMBED_INFO", 32),
    # ICCCM
    "WM_STATE": ("WM_STATE", 32),
    # Qtile-specific properties
    "QTILE_INTERNAL": ("CARDINAL", 32)
}

# TODO add everything required here:
# http://standards.freedesktop.org/wm-spec/latest/ar01s03.html
SUPPORTED_ATOMS = [
    # From http://standards.freedesktop.org/wm-spec/latest/ar01s03.html
    '_NET_SUPPORTED',
    '_NET_CLIENT_LIST',
    '_NET_CLIENT_LIST_STACKING',
    '_NET_CURRENT_DESKTOP',
    '_NET_ACTIVE_WINDOW',
    # '_NET_WORKAREA',
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
SUPPORTED_ATOMS.extend(key for key in WindowStates.keys() if key)

XCB_CONN_ERRORS = {
    1: 'XCB_CONN_ERROR',
    2: 'XCB_CONN_CLOSED_EXT_NOTSUPPORTED',
    3: 'XCB_CONN_CLOSED_MEM_INSUFFICIENT',
    4: 'XCB_CONN_CLOSED_REQ_LEN_EXCEED',
    5: 'XCB_CONN_CLOSED_PARSE_ERR',
    6: 'XCB_CONN_CLOSED_INVALID_SCREEN',
    7: 'XCB_CONN_CLOSED_FDPASSING_FAILED',
}


class MaskMap(object):
    """
        A general utility class that encapsulates the way the mask/value idiom
        works in xpyb. It understands a special attribute _maskvalue on
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
GCMasks = MaskMap(xcffib.xproto.GC)


class AtomCache(object):
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


class _Wrapper(object):
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
        self.root = Window(conn, self.root)


class PseudoScreen(object):
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


class Colormap(object):
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
            r = x8to16(int(color[-6] + color[-5], 16))
            g = x8to16(int(color[-4] + color[-3], 16))
            b = x8to16(int(color[-2] + color[-1], 16))
            return self.conn.conn.core.AllocColor(self.cid, r, g, b).reply()


class Xinerama(object):
    def __init__(self, conn):
        self.ext = conn.conn(xcffib.xinerama.key)

    def query_screens(self):
        r = self.ext.QueryScreens().reply()
        return r.screen_info


class RandR(object):
    def __init__(self, conn):
        self.ext = conn.conn(xcffib.randr.key)
        self.ext.SelectInput(
            conn.default_screen.root.wid,
            xcffib.randr.NotifyMask.ScreenChange
        )

    def query_crtcs(self, root):
        l = []
        for i in self.ext.GetScreenResources(root).reply().crtcs:
            info = self.ext.GetCrtcInfo(i, xcffib.CurrentTime).reply()
            d = dict(
                x=info.x,
                y=info.y,
                width=info.width,
                height=info.height
            )
            l.append(d)
        return l


class XFixes(object):
    selection_mask = SelectionEventMask.SetSelectionOwner | \
        SelectionEventMask.SelectionClientClose | \
        SelectionEventMask.SelectionWindowDestroy

    def __init__(self, conn):
        self.conn = conn
        self.ext = conn.conn(xcffib.xfixes.key)
        self.ext.QueryVersion(xcffib.xfixes.MAJOR_VERSION,
                              xcffib.xfixes.MINOR_VERSION)

    def select_selection_input(self, window, selection="PRIMARY"):
        SELECTION = self.conn.atoms[selection]
        self.conn.xfixes.ext.SelectSelectionInput(window.wid,
                                                  SELECTION,
                                                  self.selection_mask)


class GC(object):
    def __init__(self, conn, gid):
        self.conn = conn
        self.gid = gid

    def change(self, **kwargs):
        mask, values = GCMasks(**kwargs)
        self.conn.conn.core.ChangeGC(self.gid, mask, values)


class Window(object):
    def __init__(self, conn, wid):
        self.conn = conn
        self.wid = wid

    def _propertyString(self, r):
        """Extract a string from a window property reply message"""
        return r.value.to_string()

    def _propertyUTF8(self, r):
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
            return self._propertyUTF8(r)

        r = self.get_property("_NET_WM_NAME", "UTF8_STRING")
        if r:
            return self._propertyUTF8(r)

        r = self.get_property(
            xcffib.xproto.Atom.WM_NAME,
            xcffib.xproto.GetPropertyType.Any
        )
        if r:
            return self._propertyString(r)

    def get_wm_hints(self):
        r = self.get_property("WM_HINTS", xcffib.xproto.GetPropertyType.Any)
        if r:
            l = r.value.to_atoms()
            flags = set(k for k, v in HintsFlags.items() if l[0] & v)
            return dict(
                flags=flags,
                input=l[1] if "InputHint" in flags else None,
                initial_state=l[2] if "StateHing" in flags else None,
                icon_pixmap=l[3] if "IconPixmapHint" in flags else None,
                icon_window=l[4] if "IconWindowHint" in flags else None,
                icon_x=l[5] if "IconPositionHint" in flags else None,
                icon_y=l[6] if "IconPositionHint" in flags else None,
                icon_mask=l[7] if "IconMaskHint" in flags else None,
                window_group=l[8] if 'WindowGroupHint' in flags else None,
            )

    def get_wm_normal_hints(self):
        r = self.get_property(
            "WM_NORMAL_HINTS",
            xcffib.xproto.GetPropertyType.Any
        )
        if r:
            l = r.value.to_atoms()
            flags = set(k for k, v in NormalHintsFlags.items() if l[0] & v)
            return dict(
                flags=flags,
                min_width=l[1 + 4],
                min_height=l[2 + 4],
                max_width=l[3 + 4],
                max_height=l[4 + 4],
                width_inc=l[5 + 4],
                height_inc=l[6 + 4],
                min_aspect=l[7 + 4],
                max_aspect=l[8 + 4],
                base_width=l[9 + 4],
                base_height=l[9 + 4],
                win_gravity=l[9 + 4],
            )

    def get_wm_protocols(self):
        l = self.get_property("WM_PROTOCOLS", "ATOM", unpack=int)
        if l is not None:
            return set(self.conn.atoms.get_name(i) for i in l)
        return set()

    def get_wm_state(self):
        return self.get_property("WM_STATE", xcffib.xproto.GetPropertyType.Any, unpack=int)

    def get_wm_class(self):
        """Return an (instance, class) tuple if WM_CLASS exists, or None"""
        r = self.get_property("WM_CLASS", "STRING")
        if r:
            s = self._propertyString(r)
            return tuple(s.strip("\0").split("\0"))
        return tuple()

    def get_wm_window_role(self):
        r = self.get_property("WM_WINDOW_ROLE", "STRING")
        if r:
            return self._propertyString(r)

    def get_wm_transient_for(self):
        r = self.get_property("WM_TRANSIENT_FOR", "WINDOW", unpack=int)

        if r:
            return r[0]

    def get_wm_icon_name(self):
        r = self.get_property("_NET_WM_ICON_NAME", "UTF8_STRING")
        if r:
            return self._propertyUTF8(r)

        r = self.get_property("WM_ICON_NAME", "STRING")
        if r:
            return self._propertyUTF8(r)

    def get_wm_client_machine(self):
        r = self.get_property("WM_CLIENT_MACHINE", "STRING")
        if r:
            return self._propertyUTF8(r)

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
        # hack for negative numbers
        values = [i & 0xffffffff for i in values]
        return self.conn.conn.core.ConfigureWindow(self.wid, mask, values)

    def set_attribute(self, **kwargs):
        mask, values = AttributeMasks(**kwargs)
        self.conn.conn.core.ChangeWindowAttributesChecked(
            self.wid, mask, values
        )

    def set_cursor(self, name):
        cursorId = self.conn.cursors[name]
        mask, values = AttributeMasks(cursor=cursorId)
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
            if isinstance(value, six.string_types):
                # xcffib will pack the bytes, but we should encode them properly
                if six.PY3:
                    value = value.encode()
                elif not isinstance(value, str):
                    # This will only run for Python 2 unicode strings, can't
                    # use 'isinstance(value, unicode)' because Py 3 does not
                    # have unicode and pyflakes complains
                    value = value.encode('utf-8')
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
            logger.warning(
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
                if isinstance(prop, six.string_types)
                else prop,
                self.conn.atoms[type]
                if isinstance(type, six.string_types)
                else type,
                0, (2 ** 32) - 1
            ).reply()
        except (xcffib.xproto.WindowError, xcffib.xproto.AccessError):
            logger.warning(
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
        self.conn.conn.core.UnmapWindowChecked(self.wid).check()

    def get_attributes(self):
        return self.conn.conn.core.GetWindowAttributes(self.wid).reply()

    def create_gc(self, **kwargs):
        gid = self.conn.conn.generate_id()
        mask, values = GCMasks(**kwargs)
        self.conn.conn.core.CreateGC(gid, self.wid, mask, values)
        return GC(self.conn, gid)

    def ungrab_key(self, key, modifiers):
        """Passing None means any key, or any modifier"""
        if key is None:
            key = xcffib.xproto.Atom.Any
        if modifiers is None:
            modifiers = xcffib.xproto.ModMask.Any
        self.conn.conn.core.UngrabKey(key, self.wid, modifiers)

    def grab_key(self, key, modifiers, owner_events,
                 pointer_mode, keyboard_mode):
        self.conn.conn.core.GrabKey(
            owner_events,
            self.wid,
            modifiers,
            key,
            pointer_mode,
            keyboard_mode
        )

    def ungrab_button(self, button, modifiers):
        """Passing None means any key, or any modifier"""
        if button is None:
            button = xcffib.xproto.Atom.Any
        if modifiers is None:
            modifiers = xcffib.xproto.ModMask.Any
        self.conn.conn.core.UngrabButton(button, self.wid, modifiers)

    def grab_button(self, button, modifiers, owner_events,
                    event_mask, pointer_mode, keyboard_mode):
        self.conn.conn.core.GrabButton(
            owner_events,
            self.wid,
            event_mask,
            pointer_mode,
            keyboard_mode,
            xcffib.xproto.Atom._None,
            xcffib.xproto.Atom._None,
            button,
            modifiers,
        )

    def grab_pointer(self, owner_events, event_mask, pointer_mode,
                     keyboard_mode, cursor=None):
        self.conn.conn.core.GrabPointer(
            owner_events,
            self.wid,
            event_mask,
            pointer_mode,
            keyboard_mode,
            xcffib.xproto.Atom._None,
            cursor or xcffib.xproto.Atom._None,
            xcffib.xproto.Atom._None,
        )

    def ungrab_pointer(self):
        self.conn.conn.core.UngrabPointer(xcffib.xproto.Atom._None)

    def query_tree(self):
        q = self.conn.conn.core.QueryTree(self.wid).reply()
        root = None
        parent = None
        if q.root:
            root = Window(self.conn, q.root)
        if q.parent:
            parent = Window(self.conn, q.root)
        return root, parent, [Window(self.conn, i) for i in q.children]


class Font(object):
    def __init__(self, conn, fid):
        self.conn = conn
        self.fid = fid

    @property
    def _maskvalue(self):
        return self.fid

    def text_extents(self, s):
        s += "aaa"
        x = self.conn.conn.core.QueryTextExtents(self.fid, len(s), s).reply()
        return x


class Connection(object):
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
        self.first_sym_to_code = None
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

        first_sym_to_code = {}
        for k, s in self.code_to_syms.items():
            if s[0] and not s[0] in first_sym_to_code:
                first_sym_to_code[s[0]] = k

        self.first_sym_to_code = first_sym_to_code

    def refresh_modmap(self):
        q = self.conn.core.GetModifierMapping().reply()
        modmap = {}
        for i, k in enumerate(q.keycodes):
            l = modmap.setdefault(ModMapOrder[i // q.keycodes_per_modifier], [])
            l.append(k)
        self.modmap = modmap

    def get_modifier(self, keycode):
        """Return the modifier matching keycode"""
        for n, l in self.modmap.items():
            if keycode in l:
                return n
        return None

    def keysym_to_keycode(self, keysym):
        return self.first_sym_to_code.get(keysym, 0)

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
        return Window(self, wid)

    def disconnect(self):
        self.conn.disconnect()
        self._connected = False

    def flush(self):
        if self._connected:
            return self.conn.flush()

    def xsync(self):
        # The idea here is that pushing an innocuous request through the queue
        # and waiting for a response "syncs" the connection, since requests are
        # serviced in order.
        self.conn.core.GetInputFocus().reply()

    def grab_server(self):
        return self.conn.core.GrabServer()

    def get_setup(self):
        return self.conn.get_setup()

    def open_font(self, name):
        fid = self.conn.generate_id()
        self.conn.core.OpenFont(fid, len(name), name)
        return Font(self, fid)

    def extensions(self):
        return set(
            i.name.to_string().lower()
            for i in self.conn.core.ListExtensions().reply().names
        )
