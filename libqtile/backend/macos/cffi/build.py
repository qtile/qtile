import argparse
import glob
import os
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from cffi import FFI
from setuptools import Distribution
from setuptools.command.build_ext import build_ext

MAC_SRC_PATH = (Path(__file__).parent / ".." / "src").resolve()

CDEF = """
// display.h
struct mac_output {
    char *name;
    int x;
    int y;
    int width;
    int height;
};

int mac_get_outputs(struct mac_output **outputs, size_t *count);
void mac_free_outputs(struct mac_output *outputs, size_t count);
void mac_get_mouse_position(int *x, int *y);
void mac_warp_pointer(int x, int y);
void mac_poll_runloop(void);
void mac_simulate_keypress(uint32_t keycode, uint64_t flags);

// window_manager.h
struct mac_window {
    void *ptr; // AXUIElementRef
    uintptr_t wid;
};

void mac_window_retain(struct mac_window *win);
void mac_window_release(struct mac_window *win);

typedef void (*ax_observer_cb)(void *win_ptr, char *notification, void *userdata);
int mac_observer_start(ax_observer_cb callback, void *userdata);
void mac_observer_stop(void);

int mac_get_windows(struct mac_window **windows, size_t *count);
void mac_free_windows(struct mac_window *windows, size_t count);

int mac_get_focused_window(struct mac_window *win);
bool mac_is_window(void *ptr);

char* mac_window_get_name(struct mac_window *win);
char* mac_window_get_role(struct mac_window *win);
char* mac_window_get_app_name(struct mac_window *win);
char* mac_window_get_bundle_id(struct mac_window *win);

void mac_window_get_position(struct mac_window *win, int *x, int *y);
void mac_window_get_size(struct mac_window *win, int *width, int *height);
void mac_window_place(struct mac_window *win, int x, int y, int width, int height);
void mac_window_focus(struct mac_window *win);
void mac_window_bring_to_front(struct mac_window *win);
void mac_window_kill(struct mac_window *win);
void mac_window_set_hidden(struct mac_window *win, bool hidden);
int mac_window_get_pid(struct mac_window *win);
bool mac_window_is_visible(struct mac_window *win);
int mac_window_get_parent(struct mac_window *win, struct mac_window *parent_out);
void mac_window_set_fullscreen(struct mac_window *win, bool fullscreen);
void mac_window_set_maximized(struct mac_window *win, bool maximized);
void mac_window_set_minimized(struct mac_window *win, bool minimized);

void free(void *ptr);

// event_tap.h
typedef int (*event_tap_cb)(uint32_t type, uint64_t flags, uint32_t keycode, void *userdata);
int mac_event_tap_start(event_tap_cb callback, void *userdata);
void mac_event_tap_stop(void);
double mac_get_idle_time(void);
void mac_inhibit_idle(bool inhibit);

// drawing.h
struct mac_internal {
    void *win; // NSWindow
    void *view; // NSView
    int width;
    int height;
    void *buffer; // Image data
};

struct mac_internal* mac_internal_new(int x, int y, int width, int height);
void mac_internal_free(struct mac_internal *win);
void mac_internal_place(struct mac_internal *win, int x, int y, int width, int height);
void* mac_internal_get_buffer(struct mac_internal *win);
void mac_internal_draw(struct mac_internal *win);
void mac_internal_set_visible(struct mac_internal *win, bool visible);
void mac_internal_bring_to_front(struct mac_internal *win);
"""

SOURCE = """
#include "display.h"
#include "window_manager.h"
#include "event_tap.h"
#include "drawing.h"
"""

INCLUDE_DIRS = [
    MAC_SRC_PATH,
]

SOURCE_FILES = glob.glob(f"{MAC_SRC_PATH}/*.m") + glob.glob(f"{MAC_SRC_PATH}/*.c")
OBJECTS = [
    (Path(src).parent / "build" / Path(src).with_suffix(".o").name).as_posix()
    for src in SOURCE_FILES
]


@contextmanager
def chdir(path: Path) -> Iterator[None]:
    prev_cwd = os.getcwd()
    try:
        os.chdir(path)
        yield
    finally:
        os.chdir(prev_cwd)


def build_objects(debug: bool = False) -> None:
    if not SOURCE_FILES:
        return

    with chdir(MAC_SRC_PATH):
        dist = Distribution()
        cmd = build_ext(dist)
        cmd.setup_shlib_compiler()

        extra_preargs = ["-fobjc-arc"]
        if debug:
            extra_preargs.extend(["-g3", "-Og"])
        else:
            extra_preargs.extend(["-O2"])
        extra_preargs.extend(["-fPIC", "-Wall", "-Wextra"])

        cmd.shlib_compiler.compile(
            [os.path.basename(path) for path in SOURCE_FILES],
            output_dir="build",
            include_dirs=INCLUDE_DIRS,
            extra_preargs=extra_preargs,
        )


def ffi_compile(verbose: bool = False, debug: bool = False) -> None:
    build_objects(debug=debug)

    extra_compile_args = ["-fobjc-arc"]
    extra_link_args = [
        "-framework",
        "Cocoa",
        "-framework",
        "ApplicationServices",
        "-framework",
        "Carbon",
        "-framework",
        "IOKit",
    ]

    if debug:
        extra_compile_args.extend(["-g3", "-Og"])

    ffi = FFI()
    ffi.set_source(
        "libqtile.backend.macos._ffi",
        SOURCE,
        include_dirs=INCLUDE_DIRS,
        extra_objects=OBJECTS,
        extra_compile_args=extra_compile_args,
        extra_link_args=extra_link_args,
    )
    ffi.cdef(CDEF)
    ffi.compile(
        tmpdir=Path(__file__).parent.parent.parent.parent.parent.as_posix(), verbose=verbose
    )


if __name__ == "__main__":
    if sys.platform != "darwin":
        print("macOS backend can only be built on macOS")
        sys.exit(1)
    else:
        parser = argparse.ArgumentParser(description="Qtile macOS backend build script.")
        parser.add_argument("--debug", action="store_true", help="Add debugging symbols.")
        args = parser.parse_args()
        ffi_compile(debug=args.debug)
