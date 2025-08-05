import os
import subprocess
from pathlib import Path

from cffi import FFI

QW_PATH = (Path(__file__).parent / ".." / "qw").resolve()

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

QW_PROTO_IN_PATH = (QW_PATH / ".." / "proto").resolve()

PROTOS = [
    ["wlr-layer-shell-unstable-v1-protocol.h", f"{QW_PROTO_IN_PATH}/wlr-layer-shell-unstable-v1.xml"],
    ["xdg-shell-protocol.h", f"{WAYLAND_PROTOCOLS}/stable/xdg-shell/xdg-shell.xml"],
]

QW_PROTO_OUT_PATH = QW_PATH / "proto"
QW_PROTO_OUT_PATH.mkdir(exist_ok=True)

for proto in PROTOS:
    subprocess.run(
        [WAYLAND_SCANNER, "server-header", proto[1], QW_PROTO_OUT_PATH / proto[0]],
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

// Add XCB types for xwayland support
typedef uint32_t xcb_atom_t;
typedef uint32_t xcb_window_t;
typedef uint32_t xcb_timestamp_t;

extern "Python" void log_cb(enum wlr_log_importance importance,
                                       const char *log_str);


struct wlr_box {
	int x, y;
	int width, height;
};

struct wlr_cursor {
    struct wlr_cursor_state *state;
    double x, y;
    ...;
};

// main callbacks
typedef uint32_t xkb_keysym_t;
typedef struct _cairo_surface cairo_surface_t;
extern "Python" int keyboard_key_cb(xkb_keysym_t, uint32_t, void *userdata);
extern "Python" void manage_view_cb(struct qw_view *view, void *userdata);
extern "Python" void unmanage_view_cb(struct qw_view *view, void *userdata);
extern "Python" void cursor_motion_cb(int x, int y, void *userdata);
extern "Python" int cursor_button_cb(int button, uint32_t mask, bool pressed, int x, int y, void *userdata);
extern "Python" void on_screen_change_cb(void *userdata);
extern "Python" void on_screen_reserve_space_cb(struct qw_output *output, void *userdata);

extern "Python" int request_fullscreen_cb(bool fullscreen, void *userdata);
extern "Python" int request_maximize_cb(bool maximize, void *userdata);
extern "Python" void set_title_cb(char* title, void *userdata);
extern "Python" void set_app_id_cb(char* app_id, void *userdata);
"""

cdef_files = ["log.h", "server.h", "view.h", "util.h", "output.h", "internal-view.h", "cursor.h", "xwayland.h", "xwayland-view.h"]

for file in cdef_files:
    with open(QW_PATH / file) as f:
        in_private_data = False
        for line in f.readlines():
            if line.startswith("#"):
                continue
            if line.strip().lower().startswith("// private data"):
                in_private_data = True
                CDEF += "    ...;\n"
                continue
            if line.startswith("};") and in_private_data:
                in_private_data = False
            if in_private_data:
                continue
            CDEF += line

SOURCE = ""

for root, dirs, files in os.walk(QW_PATH):
    for file in files:
        if file.endswith(".c"):
            with open(QW_PATH / file) as f:
                SOURCE += f.read()


def get_include_path(lib):
    return subprocess.run(
        ["pkg-config", "--variable=includedir", lib], text=True, stdout=subprocess.PIPE
    ).stdout.strip()


ffi = FFI()
ffi.set_source(
    "libqtile.backend.wayland._ffi",
    SOURCE,
    libraries=["wlroots-0.19", "wayland-server", "input", "cairo"],
    define_macros=[("WLR_USE_UNSTABLE", None)],
    include_dirs=[
        os.getenv("QTILE_CAIRO_PATH", "/usr/include/cairo"),
        os.getenv("QTILE_PIXMAN_PATH", "/usr/include/pixman-1"),
        os.getenv("QTILE_LIBDRM_PATH", "/usr/include/libdrm"),
        os.getenv("QTILE_WLROOTS_PATH", "/usr/include/wlroots-0.19"),
        QW_PATH,
        QW_PROTO_OUT_PATH,
    ],
)

ffi.cdef(CDEF)
if __name__ == "__main__":
    ffi.compile()
