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
    from typing import Any

    T = TypeVar("T")


class FFIStub:
    @staticmethod
    def def_extern() -> Callable[[T], T]:
        return lambda f: f

    def __getattr__(self, name: str) -> Any:
        return None


class LibStub:
    def __getattr__(self, name: str) -> Any:
        # Return a sentinel int so enums work.
        return -1


ffi = FFIStub()
lib = LibStub()
