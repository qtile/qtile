import argparse
import glob
import os
import subprocess
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from cffi import FFI
from setuptools import Distribution
from setuptools.command.build_ext import build_ext

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
    [
        "wlr-layer-shell-unstable-v1-protocol.h",
        f"{QW_PROTO_IN_PATH}/wlr-layer-shell-unstable-v1.xml",
    ],
    [
        "wlr-output-power-management-unstable-v1-protocol.h",
        f"{QW_PROTO_IN_PATH}/wlr-output-power-management-unstable-v1.xml",
    ],
    ["xdg-shell-protocol.h", f"{WAYLAND_PROTOCOLS}/stable/xdg-shell/xdg-shell.xml"],
    [
        "pointer-constraints-unstable-v1-protocol.h",
        f"{WAYLAND_PROTOCOLS}/unstable/pointer-constraints/pointer-constraints-unstable-v1.xml",
    ],
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
enum wlr_log_importance wlr_log_get_verbosity(void);
extern "Python" void log_cb(enum wlr_log_importance importance,
                                       const char *log_str);

enum wlr_input_device_type {
    WLR_INPUT_DEVICE_KEYBOARD,
    WLR_INPUT_DEVICE_POINTER,
    WLR_INPUT_DEVICE_TOUCH,
    WLR_INPUT_DEVICE_TABLET,
    WLR_INPUT_DEVICE_TABLET_PAD,
    WLR_INPUT_DEVICE_SWITCH,
};

enum libinput_config_accel_profile {
    LIBINPUT_CONFIG_ACCEL_PROFILE_NONE = 0,
    LIBINPUT_CONFIG_ACCEL_PROFILE_FLAT = (1 << 0),
    LIBINPUT_CONFIG_ACCEL_PROFILE_ADAPTIVE = (1 << 1),
};

enum libinput_config_click_method {
        LIBINPUT_CONFIG_CLICK_METHOD_NONE = 0,
        LIBINPUT_CONFIG_CLICK_METHOD_BUTTON_AREAS = (1 << 0),
        LIBINPUT_CONFIG_CLICK_METHOD_CLICKFINGER = (1 << 1),
};

enum libinput_config_tap_button_map {
        LIBINPUT_CONFIG_TAP_MAP_LRM,
        LIBINPUT_CONFIG_TAP_MAP_LMR,
};

enum libinput_config_scroll_method {
        LIBINPUT_CONFIG_SCROLL_NO_SCROLL = 0,
        LIBINPUT_CONFIG_SCROLL_2FG = (1 << 0),
        LIBINPUT_CONFIG_SCROLL_EDGE = (1 << 1),
        LIBINPUT_CONFIG_SCROLL_ON_BUTTON_DOWN = (1 << 2),
};

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
extern "Python" void view_activation_cb(struct qw_view *view, void *userdata);
extern "Python" int keyboard_key_cb(xkb_keysym_t, uint32_t, void *userdata);
extern "Python" void manage_view_cb(struct qw_view *view, void *userdata);
extern "Python" void unmanage_view_cb(struct qw_view *view, void *userdata);
extern "Python" void cursor_motion_cb(void *userdata);
extern "Python" int cursor_button_cb(int button, uint32_t mask, bool pressed, int x, int y, void *userdata);
extern "Python" void on_screen_change_cb(void *userdata);
extern "Python" void on_screen_reserve_space_cb(struct qw_output *output, void *userdata);
extern "Python" void on_input_device_added_cb(void *userdata);
extern "Python" bool focus_current_window_cb(void *userdata);
extern "Python" void on_session_lock_cb(bool locked, void *userdata);
extern "Python" struct wlr_box get_current_output_dims_cb(void *userdata);
extern "Python" bool add_idle_inhibitor_cb(void *userdata, void *inhibitor, void *view, bool is_layer_surface, bool is_session_lock_surface);
extern "Python" bool remove_idle_inhibitor_cb(void *userdata, void *inhibitor);
extern "Python" bool check_inhibited_cb(void *userdata);

extern "Python" int request_focus_cb(void *userdata);
extern "Python" int request_close_cb(void *userdata);
extern "Python" int request_fullscreen_cb(bool fullscreen, void *userdata);
extern "Python" int request_maximize_cb(bool maximize, void *userdata);
extern "Python" int request_minimize_cb(bool minimize, void *userdata);
extern "Python" void set_title_cb(char* title, void *userdata);
extern "Python" void set_app_id_cb(char* app_id, void *userdata);
"""

cdef_files = [
    "log.h",
    "session-lock.h",
    "server.h",
    "view.h",
    "util.h",
    "output.h",
    "internal-view.h",
    "cursor.h",
    "input-device.h",
    "keyboard.h",
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

SOURCE = "\n".join(f'#include "{header}"' for header in cdef_files) + "\n"


def get_include_path(lib: str) -> str:
    return subprocess.run(
        ["pkg-config", "--variable=includedir", lib], text=True, stdout=subprocess.PIPE
    ).stdout.strip()


INCLUDE_DIRS = [
    os.getenv("QTILE_CAIRO_PATH", "/usr/include/cairo"),
    os.getenv("QTILE_PIXMAN_PATH", "/usr/include/pixman-1"),
    os.getenv("QTILE_LIBDRM_PATH", "/usr/include/libdrm"),
    os.getenv("QTILE_WLROOTS_PATH", "/usr/include/wlroots-0.19"),
    QW_PATH,
    QW_PROTO_OUT_PATH,
]
LIBRARIES = ["wlroots-0.19", "wayland-server", "input", "cairo"]
SOURCE_FILES = glob.glob(f"{QW_PATH}/*.c")
OBJECTS = [Path(src).parent / "build" / Path(src).with_suffix(".o").name for src in SOURCE_FILES]


@contextmanager
def chdir(path: Path) -> Iterator[None]:
    prev_cwd = os.getcwd()
    try:
        os.chdir(path)
        yield
    finally:
        os.chdir(prev_cwd)


def build_objects(debug: bool = False, asan: bool = False) -> None:
    # We have to use relative paths here for output_dir to work as expected
    with chdir(QW_PATH):
        dist = Distribution()
        cmd = build_ext(dist)
        cmd.setup_shlib_compiler()

        extra_preargs = []
        if debug or asan:
            extra_preargs = ["-g3", "-Og"]
        else:
            extra_preargs = ["-O2"]
        extra_preargs.extend(["-fPIC", "-Wall", "-Wextra"])

        cmd.shlib_compiler.compile(
            [os.path.basename(path) for path in SOURCE_FILES],
            output_dir="build",
            macros=[("WLR_USE_UNSTABLE", None)],
            include_dirs=INCLUDE_DIRS,
            extra_preargs=extra_preargs,
        )


def ffi_compile(verbose: bool = False, debug: bool = False, asan: bool = False) -> None:
    # The ffi source of "libqtile.backend.wayland._ffi" means that we'll compile the library file
    # at libqtile/backend/wayland/_ffi.so.
    # This is built at the path specified in tmpdir which is "." by default. So, if we're in a
    # virtual environment, libqtile might be at .venv/lib/python3.13/site-packages/ but if we run
    # the builder script, we'll get a new libqtile folder in th current directory that only has that
    # tree shown above and the libtile library won't find the `_ffi` library.
    # We therefore set the tmpdir to be the path to the folder containing libqtile so the library
    # is always created in the correct folder.
    # The compile command is nested in a function to ensure that the tmpdir value is not overwritten.
    build_objects(debug=debug, asan=asan)

    extra_compile_args = []
    extra_link_args = []
    if debug or asan:
        extra_compile_args.extend(["-g3", "-Og"])
    if asan:
        extra_compile_args.extend(
            ["-fsanitize=address,leak,undefined", "-fno-omit-frame-pointer"]
        )
        extra_link_args.extend(["-fsanitize=address,undefined"])

    ffi = FFI()
    ffi.set_source(
        "libqtile.backend.wayland._ffi",
        SOURCE,
        define_macros=[("WLR_USE_UNSTABLE", None)],
        include_dirs=INCLUDE_DIRS,
        extra_objects=OBJECTS,
        libraries=LIBRARIES,
        extra_compile_args=extra_compile_args,
        extra_link_args=extra_link_args,
    )
    ffi.cdef(CDEF)
    ffi.compile(
        tmpdir=Path(__file__).parent.parent.parent.parent.parent.as_posix(), verbose=verbose
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Qtile wayland backend build script.")
    parser.add_argument("--debug", action="store_true", help="Add debugging symbols.")
    parser.add_argument(
        "--asan", action="store_true", help="Compile with address sanitisation support."
    )
    args = parser.parse_args()
    ffi_compile(debug=args.debug, asan=args.asan)
