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
    # Always output compiled file to correct folder, regardless from where the script is called
    ffi.compile(
        tmpdir=Path(__file__).parent.parent.parent.parent.parent.as_posix(), verbose=verbose
    )


if __name__ == "__main__":
    ffi_compile()
