
import sys

from unittest.mock import MagicMock


class Mock(MagicMock):
    # xcbq does a dir() on objects and pull stuff out of them and tries to sort
    # the result. MagicMock has a bunch of stuff that can't be sorted, so let's
    # lie about dir().
    def __dir__(self):
        return []


MOCK_MODULES = [
    "libqtile._ffi_pango",
    "libqtile.backend.wayland._ffi",
    "libqtile.backend.x11._ffi_xcursors",
    "cairocffi.ffi",
    "cairocffi.xcb",
    "cairocffi.pixbuf",
    "cffi",
    "dateutil",
    "dateutil.parser",
    "dbus_next",
    "dbus_next.aio",
    "dbus_next.errors",
    "dbus_next.constants",
    "iwlib",
    "keyring",
    "mpd",
    "psutil",
    "pulsectl",
    "pulsectl_asyncio",
    "pywayland",
    "pywayland.protocol.wayland",
    "pywayland.protocol.wayland.wl_output",
    "pywayland.server",
    "pywayland.utils",
    "wlroots",
    "wlroots.helper",
    "wlroots.util",
    "wlroots.util.box",
    "wlroots.util.clock",
    "wlroots.util.edges",
    "wlroots.util.region",
    "wlroots.wlr_types",
    "wlroots.wlr_types.cursor",
    "wlroots.wlr_types.foreign_toplevel_management_v1",
    "wlroots.wlr_types.idle",
    "wlroots.wlr_types.idle_inhibit_v1",
    "wlroots.wlr_types.keyboard",
    "wlroots.wlr_types.layer_shell_v1",
    "wlroots.wlr_types.output_management_v1",
    "wlroots.wlr_types.pointer_constraints_v1",
    "wlroots.wlr_types.output",
    "wlroots.wlr_types.output_power_management_v1",
    "wlroots.wlr_types.scene",
    "wlroots.wlr_types.server_decoration",
    "wlroots.wlr_types.virtual_keyboard_v1",
    "wlroots.wlr_types.virtual_pointer_v1",
    "wlroots.wlr_types.xdg_shell",
    "xcffib",
    "xcffib.ffi",
    "xcffib.randr",
    "xcffib.render",
    "xcffib.wrappers",
    "xcffib.xfixes",
    "xcffib.xinerama",
    "xcffib.xproto",
    "xcffib.xtest",
    "xdg.IconTheme",
    "xkbcommon",
]

sys.modules.update((mod_name, Mock()) for mod_name in MOCK_MODULES)
