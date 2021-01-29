from libqtile.backend.base import Core
from libqtile.backend.x11 import xcbq
from libqtile.drawer import DrawerBackend


class StubDrawerBackend(DrawerBackend):
    def create_buffer(self, width, height):
        pass

    def create_surface(self, width, height, drawable=None):
        pass

    def copy_area(
        self,
        source,
        width,
        height,
        destination_offset_x=0,
        destination_offset_y=0,
    ):
        pass


class StubCore(Core):
    masks = (None, None)

    def __init__(self, display, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.display = display

        # We need to trick the widgets into thinking this is libqtile.qtile so
        # we add some methods that are called when the widgets are configured
        # TODO: Make this a stub too? Not sure what to do here before we have
        # multiple backends
        self.conn = xcbq.Connection(display)

    def finalize(self):
        pass

    def get_drawer_backend(self, wid):
        return StubDrawerBackend(self.conn, wid)

    @property
    def display_name(self):
        return ':0.0'

    def get_keys(self):
        return []

    def get_modifiers(self):
        return []

    def grab_key(self, key):
        return (0, 0)

    def ungrab_key(self, key):
        return (0, 0)

    def ungrab_keys(self):
        pass

    def grab_button(self, mouse):
        pass

    def ungrab_buttons(self):
        return

    def grab_pointer(self):
        pass

    def ungrab_pointer(self):
        pass

    def update_net_desktops(self, groups, index: int) -> None:
        pass
