"""Root conftest.py — loaded by pytest before any other conftest.

On macOS, cairocffi and xcffib require native X11/Cairo libraries that are
not present by default.  The macOS unit tests use FakeFFI and do not need
real Cairo/XCB at runtime, so we stub them out here before any imports that
would trigger the dlopen.  setdefault is used so real libraries loaded on
Linux/Wayland are left untouched.
"""

import sys

if sys.platform == "darwin":
    from unittest.mock import MagicMock

    for _mod in (
        "cairocffi",
        "cairocffi.ffi",
        "xcffib",
        "xcffib.ffi",
        "xcffib.xcb",
        # pango_ffi.py calls pango_ffi.include(cairocffi_ffi) which requires
        # a real cffi.FFI — mock the whole module so the include never runs.
        "libqtile.pango_ffi",
    ):
        sys.modules.setdefault(_mod, MagicMock())
