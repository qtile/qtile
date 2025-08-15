import os
from pathlib import Path

import wlroots.ffi_build as wlr
from cffi import FFI

from libqtile.backend.wayland.cffi import cairo_buffer, libinput

SOURCE = "\n".join(
    [
        wlr.SOURCE,
        libinput.SOURCE,
        cairo_buffer.SOURCE,
    ]
)

ffi = FFI()
ffi.set_source(
    "libqtile.backend.wayland._ffi",
    SOURCE,
    libraries=["wlroots", "input"],
    define_macros=[("WLR_USE_UNSTABLE", None)],
    include_dirs=[
        os.getenv("QTILE_PIXMAN_PATH", "/usr/include/pixman-1"),
        os.getenv("QTILE_LIBDRM_PATH", "/usr/include/libdrm"),
        wlr.include_dir,
    ],
)

ffi.include(wlr.ffi_builder)
ffi.cdef(libinput.CDEF)
ffi.cdef(cairo_buffer.CDEF)


def ffi_compile(verbose: bool = False) -> None:
    # The ffi source of "libqtile.backend.wayland._ffi" means that we'll compile the library file
    # at libqtile/backend/wayland/_ffi.so.
    # This is built at the path specified in tmpdir which is "." by default. So, if we're in a
    # virtual environment, libqtile might be at .venv/lib/python3.13/site-packages/ but if we run
    # the builder script, we'll get a new libqtile folder in th current directory that only has that
    # tree shown above and the libtile library won't find the `_ffi` library.
    # We therefore set the tmpdir to be the path to the folder containing libqtile so the library
    # is always created in the correct folder.
    # The compile command is nested in a function to ensure that the tmpdir value is not overwritten.
    ffi.compile(
        tmpdir=Path(__file__).parent.parent.parent.parent.parent.as_posix(), verbose=verbose
    )


if __name__ == "__main__":
    ffi_compile()
