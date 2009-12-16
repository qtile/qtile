"""
    A minimal OO layer over xpyb. This is NOT intended to be complete - it only
    implements the subset of functionalty needed by qtile.
"""
import sys
import xcb.xproto, xcb.xinerama
from xcb.xproto import CW, WindowClass, EventMask


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


class Window:
    def __init__(self, conn, wid):
        self.conn, self.wid = conn, wid

    def _get_property(self, xa, type):
        q = self.conn.core.GetProperty(
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
                xcb.xproto.GetPropertyType.Any,
            )
        if r.value_len == 0:
            return None
        else:
            # FIXME
            return toString(r.value[0])

    def get_hints(self):
        r = self._get_property(xcb.xcb.XA_WM_HINTS)
        print r.type
        print dir(r)

    def get_geometry(self):
        q = self.conn.core.GetGeometry(self.wid)
        return q.reply()

    def _change_attributes(self, mask, lst):
        self.conn.core.ChangeWindowAttributesChecked(
            self.wid,
            mask,
            lst
        )

    def set_event_mask(self, x):
        return self._change_attributes(CW.EventMask, x)

    def set_back_pixmap(self, x): raise NotImplementedError
    def set_back_pixel(self, x): raise NotImplementedError
    def set_border_pixel(self, x): raise NotImplementedError
    def set_border_pixmap(self, x): raise NotImplementedError
    def set_bit_gravity(self, x): raise NotImplementedError
    def set_win_gravity(self, x): raise NotImplementedError
    def set_backing_storej(self, x): raise NotImplementedError
    def set_backing_planes(self, x): raise NotImplementedError
    def set_backing_pixel(self, x): raise NotImplementedError
    def set_override_redirect(self, x): raise NotImplementedError
    def set_save_under(self, x): raise NotImplementedError
    def set_dont_propagate(self, x): raise NotImplementedError
    def set_colormap(self, x): raise NotImplementedError
    def set_cursor(self, x): raise NotImplementedError


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
        return Window(self.conn, wid)

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
