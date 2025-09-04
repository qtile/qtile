# This module is used to allow the documentation to build properly
# when the ffi module cannot be imported:

# ../libqtile/backend/wayland/window.py:254: in <module>
#    @ffi.def_extern()
#     ^^^^^^^^^^^^^^
# E   AttributeError: 'NoneType' object has no attribute 'def_extern'

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, TypeVar

if TYPE_CHECKING:
    T = TypeVar("T")


class FFIStub:
    @staticmethod
    def def_extern() -> Callable[[T], T]:
        return lambda f: f


ffi = FFIStub
lib = None
