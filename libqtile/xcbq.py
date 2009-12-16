"""
    A minimal OO layer over xpyb. This is NOT intended to be complete - it only
    implements the subset of functionalty needed by qtile.
"""
import sys
import xcb.xproto, xcb.xinerama
from xcb.xproto import CW, WindowClass, EventMask, ConfigWindow

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

def toStr(s):
    return "".join([chr(i) for i in s.name])


def maskmap(mmap, **kwargs):
    """
        mmap: a list of (name, maskvalue) tuples.
        kwargs: keys should be in the mmap name set

        Returns a (mask, values) tuple.
    """
    mask = 0
    values = []
    for s, m in mmap:
        val = kwargs.get(s)
        if val is not None:
            mask &= m
            values.append(val)
            del kwargs[s]
    if kwargs:
        raise ValueError("Unknown mask names: %s"%kwargs.keys())
    return mask, values


class AtomCache:
    defaults = [
        '_NET_WM_WINDOW_TYPE'
    ]
    def __init__(self, conn):
        self.conn = conn
        self.atoms = {}
        # We can change the pre-loads not to wait for a return
        for name in WindowTypes.keys():
            self.atoms[name] = self.internAtomUnchecked(name)
        for name in self.defaults:
            self.atoms[name] = self.internAtomUnchecked(name)

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


class Window:
    ConfigureMasks = (
        ("x", ConfigWindow.X),
        ("y", ConfigWindow.Y),
        ("width", ConfigWindow.Width),
        ("height", ConfigWindow.Height),
        ("border_width", ConfigWindow.BorderWidth),
        ("sibling", ConfigWindow.Sibling),
        ("stackmode", ConfigWindow.StackMode),
    )
    PropertyMasks = (
        ("backpixmap", CW.BackPixmap),
        ("backpixel", CW.BackPixel),
        ("borderpixmap", CW.BorderPixmap),
        ("borderpixel", CW.BorderPixel),
        ("bitgravity", CW.BitGravity),
        ("wingravity", CW.WinGravity),
        ("backingstore", CW.BackingStore),
        ("backingplanes", CW.BackingPlanes),
        ("backingpixel", CW.BackingPixel),
        ("overrideredirect", CW.OverrideRedirect),
        ("saveunder", CW.SaveUnder),
        ("eventmask", CW.EventMask),
        ("dontpropagate", CW.DontPropagate),
        ("colormap", CW.Colormap),
        ("cursor", CW.Cursor),
    )
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
        mask, values = maskmap(self.ConfigureMasks, **kwargs)
        return self.conn.conn.core.ConfigureWindow(self.wid, mask, values)

    def set_attribute(self, **kwargs):
        mask, values = maskmap(self.PropertyMasks, **kwargs)
        self.conn.conn.core.ChangeWindowAttributesChecked(self.wid, mask, values)

    def set_property(self, name, type, value):
        self.conn.conn.core.ChangePropertyChecked(
            self.wid
            
            
        )
        self.window.change_property(
            self.qtile.atoms[name],
            self.qtile.atoms["python"],
            8,
            marshal.dumps(data)
        )


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

    def create_window(self, x, y, width, height):
        wid = self.conn.generate_id()
        q = self.conn.core.CreateWindowChecked(
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

    def extensions(self):
        return set([toStr(i).lower() for i in self.conn.core.ListExtensions().reply().names])

