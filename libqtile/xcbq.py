
import xcb.xproto, xcb.xinerama
import xcb

def toStr(s):
    return "".join([chr(i) for i in s.name])


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

    def flush(self):
        return self.conn.flush()

    def grab_server(self):
        return self.conn.core.GrabServer()

    def get_setup(self):
        return self.conn.get_setup()

    def extensions(self):
        return set([toStr(i).lower() for i in self.conn.core.ListExtensions().reply().names])

    def internAtomUnchecked(self, name, only_if_exists=False):
        c = self.conn.core.InternAtomUnchecked(False, len(name), name)
        return c.reply().atom

