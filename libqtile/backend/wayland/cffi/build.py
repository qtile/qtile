from cffi import FFI
from pathlib import Path

import cairocffi
import os
import subprocess

qw_path = (Path(__file__).parent / ".." / "qw").resolve()

PROTOS = [
    ["xdg-shell-protocol.h", "stable/xdg-shell/xdg-shell.xml"],
]

WAYLAND_SCANNER = subprocess.run(
    ["pkg-config", "--variable=wayland_scanner", "wayland-scanner"],
    text=True,
    stdout=subprocess.PIPE,
).stdout.strip()
WAYLAND_PROTOCOLS = subprocess.run(
    ["pkg-config", "--variable=pkgdatadir", "wayland-protocols"],
    text=True,
    stdout=subprocess.PIPE,
).stdout.strip()

for proto in PROTOS:
    subprocess.run(
        [WAYLAND_SCANNER, "server-header", f"{WAYLAND_PROTOCOLS}/{proto[1]}", qw_path / proto[0]],
        text=True,
        stdout=subprocess.PIPE,
    ).stdout.strip()

CDEF = """
// logging
enum wlr_log_importance {
    WLR_SILENT,
    WLR_ERROR,
    WLR_INFO,
    WLR_DEBUG,
    ...
};
extern "Python" void log_cb(enum wlr_log_importance importance,
                                       const char *log_str);
// main callbacks
typedef void cairo_surface_t;
typedef uint32_t xkb_keysym_t;
extern "Python" int keyboard_key_cb(xkb_keysym_t, uint32_t, void *userdata);
extern "Python" void manage_view_cb(struct qw_view *view, void *userdata);
extern "Python" void unmanage_view_cb(struct qw_view *view, void *userdata);
extern "Python" void cursor_motion_cb(int x, int y, void *userdata);
extern "Python" int cursor_button_cb(int button, uint32_t mask, bool pressed, int x, int y, void *userdata);
extern "Python" void on_screen_change_cb(void *userdata);

extern "Python" int request_fullscreen_cb(bool fullscreen, void *userdata);
extern "Python" int request_maximize_cb(bool maximize, void *userdata);
"""

cdef_files = ["log.h", "server.h", "view.h", "util.h", "internal-view.h"]

for file in cdef_files:
    with open(qw_path / file) as f:
        in_private_data = False
        for line in f.readlines():
            if line.startswith("#"):
                continue
            if line.strip() == "// private data":
                in_private_data = True
                CDEF += "    ...;\n"
                continue
            if line.startswith("};") and in_private_data:
                in_private_data = False
            if in_private_data:
                continue
            CDEF += line

SOURCE = ""

for root, dirs, files in os.walk(qw_path):
    for file in files:
        if file.endswith(".c"):
            with open(qw_path / file) as f:
                SOURCE += f.read()


def get_include_path(lib):
    return subprocess.run(
        ["pkg-config", "--variable=includedir", lib], text=True, stdout=subprocess.PIPE
    ).stdout.strip()


ffi = FFI()
ffi.set_source(
    "libqtile.backend.wayland._ffi",
    SOURCE,
    libraries=["wlroots-0.18", "wayland-server", "input", "cairo"],
    define_macros=[("WLR_USE_UNSTABLE", None)],
    include_dirs=[
        os.getenv("QTILE_CAIRO_PATH", "/usr/include/cairo"),
        os.getenv("QTILE_PIXMAN_PATH", "/usr/include/pixman-1"),
        os.getenv("QTILE_LIBDRM_PATH", "/usr/include/libdrm"),
        os.getenv("QTILE_WLROOTS_PATH", "/usr/include/wlroots-0.18"),
        qw_path,
    ],
)

ffi.cdef(CDEF)
if __name__ == "__main__":
    ffi.compile()
