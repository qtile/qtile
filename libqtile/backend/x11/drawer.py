import cairocffi
import xcffib.xproto

from libqtile.drawer import DrawerBackend


class X11DrawerBackend(DrawerBackend):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._gc = self.connection.conn.generate_id()
        self.connection.conn.core.CreateGCChecked(
            self._gc,
            self.wid,
            xcffib.xproto.GC.Foreground | xcffib.xproto.GC.Background,
            [
                self.connection.default_screen.black_pixel,
                self.connection.default_screen.white_pixel,
            ],
        ).check()

    def finalize(self):
        self.connection.conn.core.FreeGC(self._gc)
        self._gc = None
        super().finalize()

    def create_buffer(self, width, height):
        pixmap = self.connection.conn.generate_id()
        self.connection.conn.core.CreatePixmapChecked(
            self.connection.default_screen.root_depth,
            pixmap,
            self.wid,
            width,
            height,
        ).check()
        return pixmap

    def free_buffer(self, buf):
        self.connections.conn.core.FreeGC(buf)
        super().free_buffer(buf)

    def create_surface(self, width, height, drawable=None):
        return cairocffi.XCBSurface(
            self.connection.conn,
            self._pixmap if drawable is None else drawable,
            self._find_root_visual(),
            width,
            height,
        )

    def _find_root_visual(self):
        for i in self.connection.default_screen.allowed_depths:
            for v in i.visuals:
                if v.visual_id == self.connection.default_screen.root_visual:
                    return v

    def copy_area(
        self,
        source,
        width,
        height,
        destination_offset_x=0,
        destination_offset_y=0,
    ):
        self.connection.conn.core.CopyArea(
            source,
            self.wid,
            self._gc,
            0,
            0,
            destination_offset_x,
            destination_offset_y,
            width,
            height
        )
