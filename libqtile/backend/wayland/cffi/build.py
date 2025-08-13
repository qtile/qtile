from cffi import FFI
from pathlib import Path

import os
import subprocess

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

cdef_files = [
    "cursor.h",
    "internal-view.h",
    "log.h",
    "output.h",
    "server.h",
    "util.h",
    "view.h",
]

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


def make_unity_build() -> list[str]:
    collected_source_files = sorted(
        str(QW_PATH / file)
        for *_, files in os.walk(QW_PATH)
        for file in files
        if file.endswith(".c")
    )

    return list(collected_source_files)


def get_include_path(lib):
    return subprocess.run(
        ["pkg-config", "--variable=includedir", lib], text=True, stdout=subprocess.PIPE
    ).stdout.strip()


ffi = FFI()

import sys

if "--verbose" in sys.argv:
    import subprocess

    def run_wrapper(fn):
        def wrapper(*args, **kwargs):
            cmd, *_ = args
            print(' '.join(cmd))

            return fn(*args, **kwargs)
        return wrapper

    # this is a hack, to print the compile commands
    subprocess.run = run_wrapper(subprocess.run)
    subprocess.check_call = run_wrapper(subprocess.check_call)


ffi.cdef(CDEF)
ffi.set_source(
    module_name="libqtile.backend.wayland._ffi",

    # this is not the real source file provider ??
    source='\n'.join(f'#include "{filename}"' for filename in cdef_files),
    # ^ we have no idea what this is, but it does not work without it

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
    # actual source list ????
    sources=make_unity_build(),
    extra_compile_args=[
        "-fanalyzer",
        "-Wall",
        "-Wextra",
        "-Wno-unused-parameter",
        "-Wunused-result",
        "-Wcast-align",
        "-Wduplicated-branches",
        "-Wduplicated-cond",
        "-Wformat=2",
        "-Wstrict-prototypes",
        "-Wunreachable-code",
        "-Wno-discarded-qualifiers",
        "-Wformat-nonliteral",
        "-Wint-conversion",
        "-Wreturn-type",
        "-Wwrite-strings",
        "-Wshadow",
    ]
)


if __name__ == "__main__":
    ffi.compile(verbose=True)
