"""
    A minimal EWMH-aware OO layer over xpyb. This is NOT intended to be
    complete - it only implements the subset of functionalty needed by qtile.
"""
import sys
import xcb.xproto, xcb.xinerama, xcb.xcb
from xcb.xproto import CW, WindowClass, EventMask
import utils, xkeysyms

keysyms = xkeysyms.keysyms

# These should be in xpyb:
ModMasks = {
    "shift": 1<<0,
    "lock":  1<<1,
    "control": 1<<2,
    "mod1": 1<<3,
    "mod2": 1<<4,
    "mod3": 1<<5,
    "mod4": 1<<6,
    "mod5": 1<<7,
}
ModMapOrder = ["shift", "lock", "control", "mod1", "mod2", "mod3", "mod4", "mod5"]


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
    "_NET_WM_STATE": ("ATOM", 32),
    "_NET_WM_DESKTOP": ("CARDINAL", 32),
    "_NET_WM_STRUT_PARTIAL": ("CARDINAL", 32),
    "_NET_WM_WINDOW_OPACITY": ("CARDINAL", 32),
    "_NET_WM_WINDOW_TYPE": ("CARDINAL", 32),
    # Qtile-specific properties
    "QTILE_INTERNAL": ("CARDINAL", 32)
}

def toStr(s):
    return "".join([chr(i) for i in s.name])


class MaskMap:
    """
        A general utility class that encapsulates the way the mask/value idiom
        works in xpyb. It understands a special attribute _maskvalue on
        objects, which will be used instead of the object value if present.
        This lets us passin a Font object, rather than Font.fid, for example.
    """
    def __init__(self, obj):
        self.mmap = []
        for i in dir(obj):
            if not i.startswith("_"):
                self.mmap.append((i.lower(), getattr(obj, i)))

    def __call__(self, **kwargs):
        """
            kwargs: keys should be in the mmap name set

            Returns a (mask, values) tuple.
        """
        mask = 0
        values = []
        for s, m in self.mmap:
            val = kwargs.get(s)
            if val is not None:
                mask |= m
                values.append(getattr(val, "_maskvalue", val))
                del kwargs[s]
        if kwargs:
            raise ValueError("Unknown mask names: %s"%kwargs.keys())
        return mask, values

ConfigureMasks = MaskMap(xcb.xproto.ConfigWindow)
AttributeMasks = MaskMap(CW)
GCMasks = MaskMap(xcb.xproto.GC)

class AtomCache:
    def __init__(self, conn):
        self.conn = conn
        self.atoms = {}
        # We can change the pre-loads not to wait for a return
        for name in WindowTypes.keys():
            self.atoms[name] = self.internAtomUnchecked(name)
        for name in PropertyMap.keys():
            self.atoms[name] = self.internAtomUnchecked(name)
        for i in dir(xcb.xcb):
            if i.startswith("XA_"):
                self.atoms[i[3:]] = getattr(xcb.xcb, i)

    def internAtomUnchecked(self, name, only_if_exists=False):
        c = self.conn.conn.core.InternAtomUnchecked(False, len(name), name)
        return c.reply().atom

    def __getitem__(self, key):
        if key not in self.atoms:
            self.atoms[key] = self.internAtomUnchecked(key)
        return self.atoms[key]


class _Wrapper:
    def __init__(self, wrapped):
        self.wrapped = wrapped

    def __getattr__(self, x):
        return getattr(self.wrapped, x)


class Screen(_Wrapper):
    def __init__(self, conn, screen):
        _Wrapper.__init__(self, screen)
        self.default_colormap = Colormap(conn, screen.default_colormap)
        self.root = Window(conn, self.root)


class Colormap:
    def __init__(self, conn, cid):
        self.conn, self.cid = conn, cid

    def alloc_color(self, color):
        """
            Flexible color allocation.
        """
        if color.startswith("#"):
            if len(color) != 7:
                raise ValueError("Invalid color: %s"%color)
            r = int(color[1] + color[2], 16)
            g = int(color[3] + color[4], 16)
            b = int(color[5] + color[6], 16)
            return self.conn.conn.core.AllocColor(self.cid, r, g, b).reply()
        else:
            return self.conn.conn.core.AllocNamedColor(self.cid, len(color), color).reply()


class Xinerama:
    def __init__(self, conn):
        self.ext = conn.conn(xcb.xinerama.key)

    def query_screens(self):
        r = self.ext.QueryScreens().reply()
        return r.screen_info


class GC:
    def __init__(self, conn, gid):
        self.conn, self.gid = conn, gid

    def change(self, **kwargs):
        mask, values = GCMasks(**kwargs)
        self.conn.conn.core.ChangeGC(self.gid, mask, values)


class Window:
    def __init__(self, conn, wid):
        self.conn, self.wid = conn, wid

    def _get_property(self, xa):
        q = self.conn.conn.core.GetProperty(
                False,
                self.wid,
                xa,
                xcb.xproto.GetPropertyType.Any,
                0, (2**32)-1
            )
        return q.reply()
            
    def get_name(self):
        r = self._get_property(
                xcb.xcb.XA_WM_NAME,
            )
        if r.value_len == 0:
            return None
        else:
            # FIXME
            return toString(r.value[0])

    def get_hints(self):
        r = self._get_property(
                xcb.xcb.XA_WM_HINTS
            )
        return list(r.value)

    def get_geometry(self):
        q = self.conn.conn.core.GetGeometry(self.wid)
        return q.reply()

    def get_wm_type(self):
        """
            http://standards.freedesktop.org/wm-spec/wm-spec-latest.html#id2551529
        """
        r = self._get_property(
                self.conn.atoms['_NET_WM_WINDOW_TYPE']
        )
        if r.value_len == 0:
            return None
        else:
            # look up wm_type
            raise NotImplementedError

    def configure(self, **kwargs):
        """
            Arguments can be: x, y, width, height, border, sibling, stackmode
        """
        mask, values = ConfigureMasks(**kwargs)
        return self.conn.conn.core.ConfigureWindow(self.wid, mask, values)

    def set_attribute(self, **kwargs):
        mask, values = AttributeMasks(**kwargs)
        self.conn.conn.core.ChangeWindowAttributes(self.wid, mask, values)

    def set_property(self, name, value, type=None, format=None):
        """
            name: String Atom name
            type: String Atom name
            format: 8, 16, 32
        """
        if name in PropertyMap:
            if type or format:
                raise ValueError, "Over-riding default type or format for property."
            type, format = PropertyMap[name]
        else:
            if None in (type, format):
                raise ValueError, "Must specify type and format for unknown property."

        if not utils.isSequenceLike(value):
            value = [value]

        buf = []
        for i in value:
            # We'll expand these conversions as we need them
            if format == 32:
                buf.append(utils.multichar(i, 4))
            elif format == 16:
                buf.append(utils.multichar(i, 2))
            elif format == 8:
                if utils.isStringLike(i):
                    # FIXME: Unicode -> bytes conversion needed here
                    buf.append(i)
                else:
                    buf.append(utils.multichar(i, 1))
        buf = "".join(buf)

        length = len(buf)/(format/8)

        # This is a real balls-up interface-wise. As I understand it, each type
        # can have a different associated size. 
        #  - value is a string of bytes. 
        #  - length is the length of the data in terms of the specified format.
        self.conn.conn.core.ChangeProperty(
            xcb.xproto.PropMode.Replace,
            self.wid,
            self.conn.atoms[name],
            self.conn.atoms[type],
            format,  # Format - 8, 16, 32
            length,
            buf
        )

    def map(self):
        self.conn.conn.core.MapWindow(self.wid)

    def create_gc(self, **kwargs):
        gid = self.conn.conn.generate_id()
        mask, values = GCMasks(**kwargs)
        self.conn.conn.core.CreateGC(gid, self.wid, mask, values)
        return GC(self.conn, gid)

    def ungrab_key(self, key, modifiers):
        """
            Passing None means any key, or any modifier.
        """
        if key is None:
            key = xcb.xproto.Atom.Any
        if modifiers is None:
            modifiers = xcb.xproto.ModMask.Any
        self.conn.conn.core.UngrabKey(key, self.wid, modifiers)

    def grab_key(self, key, modifiers, owner_events, pointer_mode, keyboard_mode):
        self.conn.conn.core.GrabKey(
            owner_events,
            self.wid,
            modifiers,
            key,
            pointer_mode,
            keyboard_mode
        )

    def query_tree(self):
        q = self.conn.conn.core.QueryTree(self.wid).reply()
        root, parent = None, None
        if q.root:
            root = Window(self.conn, q.root)
        if q.parent:
            parent = Window(self.conn, q.root)
        return root, parent, [Window(self.conn, i) for i in q.children]


class Font:
    def __init__(self, conn, fid):
        self.conn, self.fid = conn, fid

    @property
    def _maskvalue(self):
        return self.fid

    def text_extents(self, s):
        print "CONN"
        x = self.conn.conn.core.QueryTextExtents(self.fid, len(s), s)
        print "PREREPLY"
        x = x.reply()
        print "POSTREPLY"
        print x
        return x


class Connection:
    _extmap = {
        "xinerama": Xinerama,
    }
    def __init__(self, display):
        self.conn = xcb.xcb.connect(display=display)
        self.setup = self.conn.get_setup()
        extensions = self.extensions()
        for i in extensions:
            if i in self._extmap:
                setattr(self, i, self._extmap[i](self))
        self.screens = [Screen(self, i) for i in self.setup.roots]
        self.default_screen = self.screens[self.conn.pref_screen]
        self.atoms = AtomCache(self)

        self.code_to_syms = {}
        self.first_sym_to_code = None
        self.refresh_keymap()

        self.modmap = None
        self.refresh_modmap()

    def refresh_keymap(self, first=None, count=None):
        if first is None:
            first = self.setup.min_keycode
            count = self.setup.max_keycode - self.setup.min_keycode + 1
        q = self.conn.core.GetKeyboardMapping(first, count).reply()

        l = []
        sym = None
        for i, v in enumerate(q.keysyms):
            if not i%q.keysyms_per_keycode:
                if l:
                    self.code_to_syms[(i/q.keysyms_per_keycode) + first - 1] = l
                l = []
                l.append(v)
            else:
                l.append(v)
        assert len(l) == q.keysyms_per_keycode
        self.code_to_syms[first + count - 1] = l

        first_sym_to_code = {}
        for k, s in self.code_to_syms.items():
            first_sym_to_code[s[0]] = k

        self.first_sym_to_code = first_sym_to_code
    
    def refresh_modmap(self):
        q = self.conn.core.GetModifierMapping().reply()
        modmap = {}
        for i, k in enumerate(q.keycodes): 
            l = modmap.setdefault(ModMapOrder[i/q.keycodes_per_modifier], [])
            l.append(k)
        self.modmap = modmap

    def get_modifier(self, keycode):
        """
            Return the modifier matching keycode.
        """
        for n, l in self.modmap.items():
            if keycode in l:
                return n
        return None

    def keysym_to_keycode(self, keysym):
        return self.first_sym_to_code[keysym]

    def create_window(self, x, y, width, height):
        wid = self.conn.generate_id()
        q = self.conn.core.CreateWindow(
                self.default_screen.root_depth,
                wid,
                self.default_screen.root,
                x, y, width, height, 0,
                WindowClass.InputOutput,
                self.default_screen.root_visual,
                CW.BackPixel|CW.EventMask,
                [
                    self.default_screen.black_pixel,
                    EventMask.StructureNotify|EventMask.Exposure
                ]
        )
        return Window(self, wid)

    def flush(self):
        return self.conn.flush()

    def grab_server(self):
        return self.conn.core.GrabServer()

    def get_setup(self):
        return self.conn.get_setup()

    def open_font(self, name):
        fid = self.conn.generate_id()
        self.conn.core.OpenFont(fid, len(name), name)
        return Font(self, fid)

    def extensions(self):
        return set([toStr(i).lower() for i in self.conn.core.ListExtensions().reply().names])

