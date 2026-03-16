from __future__ import annotations

import sys
from unittest.mock import MagicMock

import pytest

from test.backend.macos.fake_ffi import make_fake_ffi


@pytest.fixture
def fake_window():
    """Return a Window instance backed by FakeFfi + FakeLib.

    The Window class imports ``_ffi`` at module level, so we patch
    ``sys.modules`` before importing to inject our fakes.
    """
    ffi, lib = make_fake_ffi()

    # Build a fake _ffi module
    fake_ffi_mod = MagicMock()
    fake_ffi_mod.ffi = ffi
    fake_ffi_mod.lib = lib

    with pytest.MonkeyPatch.context() as mp:
        mp.setitem(sys.modules, "libqtile.backend.macos._ffi", fake_ffi_mod)

        # Re-import (or force reload) so the module picks up the patched _ffi
        if "libqtile.backend.macos.window" in sys.modules:
            mp.delitem(sys.modules, "libqtile.backend.macos.window")

        from libqtile.backend.macos.window import Window

        qtile = MagicMock()

        # Build a minimal win_struct mock
        win_struct = MagicMock()
        win_struct.wid = 42

        win = Window(qtile, win_struct)
        yield win


def test_window_info_keys(fake_window):
    """Window.info() must return a dict with the required keys."""
    info = fake_window.info()
    for key in ("name", "x", "y", "width", "height", "group", "id", "wm_class"):
        assert key in info, f"Missing key: {key!r}"


def test_window_get_wm_class_returns_two_element_list_or_none(fake_window):
    """get_wm_class() should return a 2-element list or None."""
    result = fake_window.get_wm_class()
    # With NULL pointers from FakeLib, result should be None
    # (both app_name_ptr and bundle_id_ptr equal NULL==0)
    assert result is None or (isinstance(result, list) and len(result) == 2)


def test_window_fullscreen_defaults_false(fake_window):
    assert fake_window.fullscreen is False


def test_window_minimized_defaults_false(fake_window):
    assert fake_window.minimized is False


def test_window_maximized_defaults_false(fake_window):
    assert fake_window.maximized is False


def test_window_wid_is_int(fake_window):
    assert isinstance(fake_window.wid, int)


def test_window_fullscreen_setter_calls_native(fake_window):
    """Setting fullscreen updates the backing field and calls mac_window_set_fullscreen."""
    lib = fake_window._lib
    fake_window.fullscreen = True
    assert fake_window.fullscreen is True
    lib.mac_window_set_fullscreen.assert_called_with(fake_window._win, True)

    fake_window.fullscreen = False
    assert fake_window.fullscreen is False
    lib.mac_window_set_fullscreen.assert_called_with(fake_window._win, False)


def test_window_maximized_setter_calls_native(fake_window):
    """Setting maximized updates the backing field and calls mac_window_set_maximized."""
    lib = fake_window._lib
    fake_window.maximized = True
    assert fake_window.maximized is True
    lib.mac_window_set_maximized.assert_called_with(fake_window._win, True)

    fake_window.maximized = False
    assert fake_window.maximized is False
    lib.mac_window_set_maximized.assert_called_with(fake_window._win, False)


def test_window_minimized_setter_calls_native(fake_window):
    """Setting minimized updates the backing field and calls mac_window_set_minimized."""
    lib = fake_window._lib
    fake_window.minimized = True
    assert fake_window.minimized is True
    lib.mac_window_set_minimized.assert_called_with(fake_window._win, True)

    fake_window.minimized = False
    assert fake_window.minimized is False
    lib.mac_window_set_minimized.assert_called_with(fake_window._win, False)


def test_window_floating_setter_notifies_group(fake_window):
    """floating setter calls group.mark_floating when a group is assigned."""
    from unittest.mock import MagicMock

    group = MagicMock()
    fake_window._group = group

    fake_window.floating = True
    group.mark_floating.assert_called_with(fake_window, True)

    fake_window.floating = False
    group.mark_floating.assert_called_with(fake_window, False)


def test_window_geometry_setters_call_native_place(fake_window):
    """x/y/width/height setters call mac_window_place with updated values."""
    lib = fake_window._lib
    # Reset call count from __init__
    lib.mac_window_place.reset_mock()

    fake_window.x = 10
    lib.mac_window_place.assert_called_with(
        fake_window._win, 10, fake_window._y, fake_window._width, fake_window._height
    )

    fake_window.y = 20
    lib.mac_window_place.assert_called_with(
        fake_window._win, fake_window._x, 20, fake_window._width, fake_window._height
    )

    fake_window.width = 800
    lib.mac_window_place.assert_called_with(
        fake_window._win, fake_window._x, fake_window._y, 800, fake_window._height
    )

    fake_window.height = 600
    lib.mac_window_place.assert_called_with(
        fake_window._win, fake_window._x, fake_window._y, fake_window._width, 600
    )
