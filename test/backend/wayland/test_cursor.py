"""Tests for Wayland cursor functionality."""

import pytest

pytest.importorskip("libqtile.backend.wayland.core")

# Shape constants from wp-cursor-shape-v1 protocol
# See: https://wayland.app/protocols/cursor-shape-v1
#
# 1 = default (pointer/arrow)
# 2 = context-menu
# 3 = help
# 4 = pointer
# 5 = progress
# 6 = wait
# 7 = cell
# 8 = crosshair
# 9 = text
# 10 = vertical-text
# ...

SHAPE_DEFAULT = 1
SHAPE_TEXT = 9
SHAPE_CROSSHAIR = 8
SHAPE_POINTER = 4


def test_cursor_shape_text(wmanager):
    """Test that text cursor shape can be set via wp-cursor-shape-v1 protocol."""
    wmanager.test_window("test_win")

    wmanager.c.eval(
        f"""
from libqtile.backend.wayland._ffi import ffi, lib
lib.qw_cursor_set_shape(self.core.qw_cursor, {SHAPE_TEXT})
cursor = self.core.qw_cursor
if cursor.current_shape_name != ffi.NULL:
    self.core._test_cursor_name = ffi.string(cursor.current_shape_name).decode('utf-8')
else:
    self.core._test_cursor_name = None
    """.strip()
    )

    cursor_name = wmanager.c.eval("self.core._test_cursor_name")

    assert cursor_name == "text", f"Got cursor_name: {cursor_name}"


def test_cursor_shape_crosshair(wmanager):
    """Test setting crosshair cursor shape."""
    wmanager.test_window("test_win")

    wmanager.c.eval(
        f"""
from libqtile.backend.wayland._ffi import ffi, lib
lib.qw_cursor_set_shape(self.core.qw_cursor, {SHAPE_CROSSHAIR})
cursor = self.core.qw_cursor
if cursor.current_shape_name != ffi.NULL:
    self.core._test_cursor_name = ffi.string(cursor.current_shape_name).decode('utf-8')
else:
    self.core._test_cursor_name = None
    """.strip()
    )

    cursor_name = wmanager.c.eval("self.core._test_cursor_name")
    assert cursor_name == "crosshair", f"Got cursor_name: {cursor_name}"


def test_cursor_shape_default(wmanager):
    """Test setting default/pointer cursor shape."""
    wmanager.test_window("test_win")

    wmanager.c.eval(
        f"""
from libqtile.backend.wayland._ffi import ffi, lib
lib.qw_cursor_set_shape(self.core.qw_cursor, {SHAPE_DEFAULT})
cursor = self.core.qw_cursor
if cursor.current_shape_name != ffi.NULL:
    self.core._test_cursor_name = ffi.string(cursor.current_shape_name).decode('utf-8')
else:
    self.core._test_cursor_name = None
    """.strip()
    )

    cursor_name = wmanager.c.eval("self.core._test_cursor_name")
    assert cursor_name in ["default", "left_ptr"], f"Got cursor_name: {cursor_name}"
