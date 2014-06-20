"""
    A minimal EWMH-aware OO layer over xpyb. This is NOT intended to be
    complete - it only implements the subset of functionalty needed by qtile.
"""
from xcffib.xproto import CW, WindowClass, EventMask
import struct
import utils
import xcffib.xcb
import xcffib.randr
import xcffib.xinerama
import xcffib.xproto
import xkeysyms


# hack xcffib.xproto for negative numbers
def ConfigureWindow(self, window, value_mask, value_list):
    import cStringIO
    from struct import pack
    from array import array
    buf = cStringIO.StringIO()
    buf.write(pack('xx2xIH2x', window, value_mask))
    buf.write(str(buffer(array('i', value_list))))
    return self.send_request(12, buf)
xcffib.xproto.xprotoExtension.ConfigureWindow = ConfigureWindow

keysyms = xkeysyms.keysyms

# These should be in xpyb:
ModMasks = {
    "shift": 1 << 0,
    "lock":  1 << 1,
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

WindowStates = {
    None: 'normal',
    '_NET_WM_STATE_FULLSCREEN': 'fullscreen',
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

    # ICCCM
    "WM_STATE": ("WM_STATE", 32),
    # Qtile-specific properties
    "QTILE_INTERNAL": ("CARDINAL", 32)
}

# TODO add everything required here
# http://standards.freedesktop.org/wm-spec/1.4/ar01s03.html
SUPPORTED_ATOMS = [
    '_NET_SUPPORTED',
    '_NET_WM_STATE',
    '_NET_WM_STATE_FULLSCREEN',
    '_NET_SUPPORTING_WM_CHECK',
    '_NET_WM_NAME',
    '_NET_WM_STRUT',
    '_NET_WM_STRUT_PARTIAL',
]

XCB_CONN_ERRORS = {
    1: 'XCB_CONN_ERROR',
    2: 'XCB_CONN_CLOSED_EXT_NOTSUPPORTED',
    3: 'XCB_CONN_CLOSED_MEM_INSUFFICIENT',
    4: 'XCB_CONN_CLOSED_REQ_LEN_EXCEED',
    5: 'XCB_CONN_CLOSED_PARSE_ERR',
    6: 'XCB_CONN_CLOSED_INVALID_SCREEN',
    7: 'XCB_CONN_CLOSED_FDPASSING_FAILED',
}

def toStr(s):
    #return "".join([chr(i) for i in s.name])
    return s.name.to_string()


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
            raise ValueError("Unknown mask names: %s" % kwargs.keys())
        return mask, values

ConfigureMasks = MaskMap(xcffib.xproto.ConfigWindow)
AttributeMasks = MaskMap(CW)
GCMasks = MaskMap(xcffib.xproto.GC)


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
        self.root = Window(conn, self.root)
        # FIXME: Where is the right place to set the cursor?
        #self.root.set_cursor("Normal")


class PseudoScreen:
    """
        This may be a Xinerama screen or a RandR CRTC, both of which are
        rectagular sections of an actual Screen.
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
        if color.startswith("#"):
            if len(color) != 7:
                raise ValueError("Invalid color: %s" % color)

            def x8to16(i):
                return 0xffff * (i & 0xff) / 0xff
            r = x8to16(int(color[1] + color[2], 16))
            g = x8to16(int(color[3] + color[4], 16))
            b = x8to16(int(color[5] + color[6], 16))
            return self.conn.conn.core.AllocColor(self.cid, r, g, b).reply()
        else:
            return self.conn.conn.core.AllocNamedColor(
                self.cid, len(color), color
            ).reply()


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
        l = []
        for i in self.ext.GetScreenResources(root).reply().crtcs:
            info = self.ext.GetCrtcInfo(i, xcffib.xcb.CurrentTime).reply()
            d = dict(
                x=info.x,
                y=info.y,
                width=info.width,
                height=info.height
            )
            l.append(d)
        return l


class GC:
    def __init__(self, conn, gid):
        self.conn = conn
        self.gid = gid

    def change(self, **kwargs):
        mask, values = GCMasks(**kwargs)
        self.conn.conn.core.ChangeGC(self.gid, mask, values)


class Window:
    def __init__(self, conn, wid):
        self.conn = conn
        self.wid = wid

    def _propertyString(self, r):
        """
            Extract a string from a window property reply message.
        """
        return r.value.to_string()

    def send_event(self, eventbuf, mask=EventMask.NoEvent):
        self.conn.conn.core.SendEvent(False, self.wid, mask, eventbuf)

    def kill_client(self):
        self.conn.conn.core.KillClient(self.wid)

    def set_input_focus(self):
        self.conn.conn.core.SetInputFocus(
            xcffib.xproto.InputFocus.PointerRoot,
            self.wid,
            xcffib.xproto.Time.CurrentTime
        )

    def warp_pointer(self, x, y):
        self.conn.conn.core.WarpPointer(
            0,
            self.wid,
            0,
            0,
            0,
            0,
            x,
            y
        )

    def get_name(self):
        """
            Tries to retrieve a canonical window name. We test the following
            properties in order of preference: _NET_WM_VISIBLE_NAME,
            _NET_WM_NAME, WM_NAME.
        """
        r = self.get_property(
            "_NET_WM_VISIBLE_NAME",
            xcffib.xproto.GetPropertyType.Any
        )
        if r:
            return self._propertyString(r)

        r = self.get_property("_NET_WM_NAME", xcffib.xproto.GetPropertyType.Any)
        if r:
            return self._propertyString(r)

        r = self.get_property(
            xcffib.xproto.Atom.WM_NAME,
            xcffib.xproto.GetPropertyType.Any
        )
        if r:
            return self._propertyString(r)

    def get_wm_hints(self):
        r = self.get_property("WM_HINTS", xcffib.xproto.GetPropertyType.Any)
        if r:
            data = struct.pack("c" * len(r.value), *(list(r.value)))
            l = struct.unpack_from("=IIIIIIIII", data)
            flags = set()
            for k, v in HintsFlags.items():
                if l[0] & v:
                    flags.add(k)
            return dict(
                flags=flags,
                input=l[1],
                initial_state=l[2],
                icon_pixmap=l[3],
                icon_window=l[4],
                icon_x=l[5],
                icon_y=l[6],
                icon_mask=l[7],
                window_group=l[8]
            )

    def get_wm_normal_hints(self):
        r = self.get_property(
            "WM_NORMAL_HINTS",
            xcffib.xproto.GetPropertyType.Any
        )
        if r:
            data = struct.pack("c" * len(r.value), *(list(r.value)))
            l = struct.unpack_from("=IIIIIIIIIIIIII", data)
            flags = set()
            for k, v in NormalHintsFlags.items():
                if l[0] & v:
                    flags.add(k)
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
        r = self.get_property("WM_PROTOCOLS", xcffib.xproto.GetPropertyType.Any)
        if r:
            data = struct.pack("c" * len(r.value), *(list(r.value)))
            l = struct.unpack_from("=" + "L" * r.value_len, data)
            return set([self.conn.atoms.get_name(i) for i in l])
        else:
            return set()

    def get_wm_state(self):
        r = self.get_property("WM_STATE", xcffib.xproto.GetPropertyType.Any)
        if r:
            return struct.unpack('=LL', ''.join(r.value))

    def get_wm_class(self):
        """
            Return an (instance, class) tuple if WM_CLASS exists, or None.
        """
        r = self.get_property("WM_CLASS", "STRING")
        if r:
            s = self._propertyString(r)
            return tuple(s.strip("\0").split("\0"))

    def get_wm_window_role(self):
        r = self.get_property("WM_WINDOW_ROLE", "STRING")
        if r:
            return self._propertyString(r)

    def get_wm_transient_for(self):
        r = self.get_property("WM_TRANSIENT_FOR", "ATOM")
        if r:
            return list(r.value)

    def get_wm_icon_name(self):
        r = self.get_property("WM_ICON_NAME", "UTF8_STRING")
        if r:
            return self._propertyString(r)

    def get_wm_client_machine(self):
        r = self.get_property("WM_CLIENT_MACHINE", "UTF8_STRING")
        if r:
            return self._propertyString(r)

    def get_geometry(self):
        q = self.conn.conn.core.GetGeometry(self.wid)
        return q.reply()

    def get_wm_desktop(self):
        r = self.get_property("_NET_WM_DESKTOP", "CARDINAL")
        if r:
            return r.value[0]

    def get_wm_type(self):
        """
        http://standards.freedesktop.org/wm-spec/wm-spec-latest.html#id2551529
        """
        r = self.get_property('_NET_WM_WINDOW_TYPE', "ATOM", unpack='I')
        if r:
            name = self.conn.atoms.get_name(r[0])
            return WindowTypes.get(name, name)

    def get_net_wm_state(self):
        # TODO: _NET_WM_STATE is a *list* of atoms
        # We're returning only the first one, but we don't need anything
        # other than _NET_WM_STATE_FULLSCREEN (at least for now)
        # Fixing this requires refactoring each call to use a list instead
        r = self.get_property('_NET_WM_STATE', "ATOM", unpack='I')
        if r:
            name = self.conn.atoms.get_name(r[0])
            return WindowStates.get(name, name)

    def get_net_wm_pid(self):
        r = self.get_property("_NET_WM_PID", unpack="I")
        if r:
            return r[0]

    def configure(self, **kwargs):
        """
            Arguments can be: x, y, width, height, border, sibling, stackmode
        """
        mask, values = ConfigureMasks(**kwargs)
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
            name: String Atom name
            type: String Atom name
            format: 8, 16, 32
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

        if not utils.isSequenceLike(value):
            value = [value]

        buf = []
        for i in value:
            # We'll expand these conversions as we need them
            if format == 32:
                buf.append(struct.pack("=L", i))
            elif format == 16:
                buf.append(struct.pack("=H", i))
            elif format == 8:
                if utils.isStringLike(i):
                    # FIXME: Unicode -> bytes conversion needed here
                    buf.append(i)
                else:
                    buf.append(struct.pack("=B", i))
        buf = "".join(buf)

        length = len(buf) / (format / 8)

        # This is a real balls-up interface-wise. As I understand it, each type
        # can have a different associated size.
        #  - value is a string of bytes.
        #  - length is the length of the data in terms of the specified format.
        self.conn.conn.core.ChangeProperty(
            xcffib.xproto.PropMode.Replace,
            self.wid,
            self.conn.atoms[name],
            self.conn.atoms[type],
            format,  # Format - 8, 16, 32
            length,
            buf
        )

    def get_property(self, prop, type=None, unpack=None):
        """
            Return the contents of a property as a GetPropertyReply, or
            a tuple of values if unpack is specified, which is a format
            string to be used with the struct module.
        """
        if type is None:
            if not prop in PropertyMap:
                raise ValueError(
                    "Must specify type for unknown property."
                )
            else:
                type, _ = PropertyMap[prop]
        try:
            r = self.conn.conn.core.GetProperty(
                False, self.wid,
                self.conn.atoms[prop]
                if isinstance(prop, basestring)
                else prop,
                self.conn.atoms[type]
                if isinstance(type, basestring)
                else type,
                0, (2 ** 32) - 1
            ).reply()

            if not r.value_len:
                return None
            elif unpack is not None:
                return struct.unpack_from(unpack, r.value.buf())
            else:
                return r
        except xcffib.xproto.WindowError:
            return None

    def list_properties(self):
        r = self.conn.conn.core.ListProperties(self.wid).reply()
        return [self.conn.atoms.get_name(i) for i in r.atoms]

    def map(self):
        self.conn.conn.core.MapWindow(self.wid)

    def unmap(self):
        self.conn.conn.core.UnmapWindow(self.wid)

    def get_attributes(self):
        return self.conn.conn.core.GetWindowAttributes(self.wid).reply()

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
        """
            Passing None means any key, or any modifier.
        """
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


class Font:
    def __init__(self, conn, fid):
        self.conn = conn
        self.fid = fid

    @property
    def _maskvalue(self):
        return self.fid

    def text_extents(self, s):
        s = s + "aaa"
        print s
        x = self.conn.conn.core.QueryTextExtents(self.fid, len(s), s).reply()
        print x
        return x


class Connection:
    _extmap = {
        "xinerama": Xinerama,
        "randr": RandR,
    }

    def __init__(self, display):
        self.conn = xcffib.xcb.connect(display=display)
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

    def refresh_keymap(self, first=None, count=None):
        if first is None:
            first = self.setup.min_keycode
            count = self.setup.max_keycode - self.setup.min_keycode + 1
        q = self.conn.core.GetKeyboardMapping(first, count).reply()

        l = []
        for i, v in enumerate(q.keysyms):
            if not i % q.keysyms_per_keycode:
                if l:
                    self.code_to_syms[
                        (i / q.keysyms_per_keycode) + first - 1
                    ] = l
                l = []
                l.append(v)
            else:
                l.append(v)
        assert len(l) == q.keysyms_per_keycode
        self.code_to_syms[first + count - 1] = l

        first_sym_to_code = {}
        for k, s in self.code_to_syms.items():
            if s[0] and not s[0] in first_sym_to_code:
                first_sym_to_code[s[0]] = k

        self.first_sym_to_code = first_sym_to_code

    def refresh_modmap(self):
        q = self.conn.core.GetModifierMapping().reply()
        modmap = {}
        for i, k in enumerate(q.keycodes):
            l = modmap.setdefault(ModMapOrder[i / q.keycodes_per_modifier], [])
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
        # The idea here is that pushing an innocuous request through
        # the queue and waiting for a response "syncs" the connection, since
        # requests are serviced in order.
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
        return set([
            toStr(i).lower()
            for i in self.conn.core.ListExtensions().reply().names
        ])


# Stolen from samurai-x
# (Don't know where to put it, so I'll put it here)
# XCB cursors doesn't want to be themed, libxcursor
# would be better choice I think
# and we (indirectly) depend on it anyway...
class Cursors(dict):
    def __init__(self, conn):
        self.conn = conn

        FLEUR = 52
        LEFT_PTR = 68
        SIZING = 120
        BOTTOM_LEFT_CORNER = 12
        BOTTOM_RIGHT_CORNER = 14
        TOP_LEFT_CORNER = 134
        TOP_RIGHT_CORNER = 136
        DOUBLE_ARROW_HORIZ = 108
        DOUBLE_ARROW_VERT = 116

        cursors = (
            ('Normal', LEFT_PTR),
            ('Resize', SIZING),
            ('ResizeH', DOUBLE_ARROW_HORIZ),
            ('ResizeV', DOUBLE_ARROW_VERT),
            ('Move', FLEUR),
            ('TopRight', TOP_RIGHT_CORNER),
            ('TopLeft', TOP_LEFT_CORNER),
            ('BotRight', BOTTOM_RIGHT_CORNER),
            ('BotLeft', BOTTOM_LEFT_CORNER),
        )

        for name, cursor_font in cursors:
            self._new(name, cursor_font)

    def _new(self, name, cursor_font):
        fid = self.conn.conn.generate_id()
        self.conn.conn.core.OpenFont(fid, len("cursor"), "cursor")
        cursor = self.conn.conn.generate_id()
        self.conn.conn.core.CreateGlyphCursor(
            cursor, fid, fid,
            cursor_font, cursor_font + 1,
            0, 0, 0,
            65535, 65535, 65535
        )
        self[name] = cursor
