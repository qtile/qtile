from __future__ import annotations

import typing

import cairocffi

from libqtile.backend import base
from libqtile.backend.macos import _ffi  # type: ignore

if typing.TYPE_CHECKING:
    from typing import Any


class Drawer(base.Drawer):
    def __init__(self, win: Internal, width: int, height: int):
        base.Drawer.__init__(self, win, width, height)
        self._win = win

    def _draw(
        self,
        offsetx: int = 0,
        offsety: int = 0,
        width: int | None = None,
        height: int | None = None,
        src_x: int = 0,
        src_y: int = 0,
    ):
        # We draw our surface to the internal window's buffer
        if not self._win._ptr:  # type: ignore
            return

        # Get the buffer from C
        buf_ptr = self._win._lib.mac_internal_get_buffer(self._win._ptr)  # type: ignore
        if buf_ptr == self._win._ffi.NULL:  # type: ignore
            return

        # Create an ImageSurface from this buffer
        # macOS buffer is RGBA (4 bytes per pixel)
        surface = cairocffi.ImageSurface(
            cairocffi.FORMAT_ARGB32,
            self._win.width,
            self._win.height,
            data=buf_ptr,
            stride=self._win.width * 4,
        )

        with cairocffi.Context(surface) as context:
            context.set_operator(cairocffi.OPERATOR_SOURCE)
            context.set_source_surface(self.surface, offsetx - src_x, offsety - src_y)
            context.rectangle(offsetx, offsety, width or self.width, height or self.height)
            context.fill()

        # Notify C to refresh the window
        self._win._lib.mac_internal_draw(self._win._ptr)  # type: ignore


class Internal(base.Internal):
    def __init__(self, qtile: Any, x: int, y: int, width: int, height: int):
        base.Internal.__init__(self)
        self.qtile = qtile

        self._ffi = _ffi.ffi
        self._lib = _ffi.lib
        self._x = x
        self._y = y
        self._width = width
        self._height = height

        # Create native window
        self._ptr = self._lib.mac_internal_new(x, y, width, height)
        self._ffi.gc(self._ptr, self._lib.mac_internal_free)

    @property
    def wid(self) -> int:
        return int(self._ffi.cast("uintptr_t", self._ptr))

    @property
    def x(self) -> int:
        return self._x

    @x.setter
    def x(self, val: int) -> None:
        self._x = val
        self._lib.mac_internal_place(self._ptr, self._x, self._y, self._width, self._height)

    @property
    def y(self) -> int:
        return self._y

    @y.setter
    def y(self, val: int) -> None:
        self._y = val
        self._lib.mac_internal_place(self._ptr, self._x, self._y, self._width, self._height)

    @property
    def width(self) -> int:
        return self._width

    @width.setter
    def width(self, val: int) -> None:
        self._width = val
        self._lib.mac_internal_place(self._ptr, self._x, self._y, self._width, self._height)

    @property
    def height(self) -> int:
        return self._height

    @height.setter
    def height(self, val: int) -> None:
        self._height = val
        self._lib.mac_internal_place(self._ptr, self._x, self._y, self._width, self._height)

    def hide(self) -> None:
        self._lib.mac_internal_set_visible(self._ptr, False)

    def unhide(self) -> None:
        self._lib.mac_internal_set_visible(self._ptr, True)

    def kill(self) -> None:
        self.hide()
        # Resources will be freed by gc when this object is deleted

    def place(
        self,
        x,
        y,
        width,
        height,
        borderwidth,
        bordercolor,
        above=False,
        margin=None,
        respect_hints=False,
    ):
        self._x = x
        self._y = y
        self._width = width
        self._height = height
        self._lib.mac_internal_place(self._ptr, x, y, width, height)
        if above:
            self.bring_to_front()

    def info(self) -> dict[str, Any]:
        return dict(
            x=self._x,
            y=self._y,
            width=self._width,
            height=self._height,
            id=self.wid,
        )

    def create_drawer(self, width: int, height: int) -> Drawer:
        return Drawer(self, width, height)

    def bring_to_front(self) -> None:
        self._lib.mac_internal_bring_to_front(self._ptr)
