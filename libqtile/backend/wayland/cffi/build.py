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
        "/usr/include/pixman-1",
        "/usr/include/libdrm",
        wlr.include_dir,
    ],
)

ffi.include(wlr.ffi_builder)
ffi.cdef(libinput.CDEF)
ffi.cdef(cairo_buffer.CDEF)

if __name__ == "__main__":
    ffi.compile()
