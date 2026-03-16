from __future__ import annotations

import sys
from unittest.mock import MagicMock

import pytest

from test.backend.macos.fake_ffi import make_fake_ffi


@pytest.fixture
def patched_drawer_module():
    """Patch ``libqtile.backend.macos._ffi`` and reload ``drawer`` module."""
    ffi, lib = make_fake_ffi()

    fake_ffi_mod = MagicMock()
    fake_ffi_mod.ffi = ffi
    fake_ffi_mod.lib = lib

    with pytest.MonkeyPatch.context() as mp:
        mp.setitem(sys.modules, "libqtile.backend.macos._ffi", fake_ffi_mod)

        # Remove any cached drawer module so it re-imports with our fakes
        for mod_name in list(sys.modules.keys()):
            if "macos.drawer" in mod_name:
                mp.delitem(sys.modules, mod_name)

        from libqtile.backend.macos.drawer import Drawer, Internal

        yield Drawer, Internal, ffi, lib


def test_internal_place_does_not_crash(patched_drawer_module):
    """Internal.place() with FakeFFI should not raise."""
    Drawer, Internal, ffi, lib = patched_drawer_module  # noqa: N806
    qtile = MagicMock()
    internal = Internal(qtile, 0, 0, 100, 50)
    # Should not raise
    internal.place(10, 20, 200, 100, 0, None)
    assert internal.x == 10
    assert internal.y == 20
    assert internal.width == 200
    assert internal.height == 100


def test_drawer_can_be_instantiated(patched_drawer_module):
    """Drawer can be instantiated with a FakeFFI-backed Internal window."""
    Drawer, Internal, ffi, lib = patched_drawer_module  # noqa: N806
    qtile = MagicMock()
    internal = Internal(qtile, 0, 0, 100, 50)
    drawer = internal.create_drawer(100, 50)
    assert drawer is not None
    assert isinstance(drawer, Drawer)


def test_internal_info(patched_drawer_module):
    """Internal.info() returns a dict with expected keys."""
    Drawer, Internal, ffi, lib = patched_drawer_module  # noqa: N806
    qtile = MagicMock()
    internal = Internal(qtile, 5, 10, 800, 600)
    info = internal.info()
    assert info["x"] == 5
    assert info["y"] == 10
    assert info["width"] == 800
    assert info["height"] == 600
    assert "id" in info


def test_drawer_draw_passes_stride_to_image_surface(patched_drawer_module):
    """Drawer._draw() must pass stride=width*4 to cairocffi.ImageSurface."""
    import unittest.mock as mock

    Drawer, Internal, ffi, lib = patched_drawer_module  # noqa: N806

    # Make buf_ptr non-NULL so _draw proceeds past the NULL check
    non_null_buf = mock.MagicMock()
    non_null_buf.__eq__ = lambda self, other: False  # != NULL
    lib.mac_internal_get_buffer.return_value = non_null_buf
    # Also make _ptr truthy
    qtile = mock.MagicMock()
    internal = Internal(qtile, 0, 0, 100, 50)
    internal._ptr = mock.MagicMock()  # truthy

    drawer = internal.create_drawer(100, 50)

    with mock.patch("cairocffi.ImageSurface") as mock_surface_cls:
        mock_surface_cls.return_value.__enter__ = mock.MagicMock(return_value=mock.MagicMock())
        mock_surface_cls.return_value.__exit__ = mock.MagicMock(return_value=False)
        # _draw needs a valid surface attribute
        drawer._surface = mock.MagicMock()
        drawer.surface = mock.MagicMock()
        try:
            drawer._draw()
        except Exception:
            pass
        mock_surface_cls.assert_called_once()
        _, kwargs = mock_surface_cls.call_args
        assert "stride" in kwargs, "stride parameter missing from ImageSurface call"
        assert kwargs["stride"] == 100 * 4, f"Expected stride=400, got {kwargs.get('stride')}"


def test_internal_property_setters(patched_drawer_module):
    """Setting x/y/width/height via property setters updates geometry and calls native place."""
    Drawer, Internal, ffi, lib = patched_drawer_module  # noqa: N806
    qtile = MagicMock()
    internal = Internal(qtile, 0, 0, 100, 50)
    call_count = lib.mac_internal_place.call_count

    internal.x = 10
    assert internal.x == 10
    assert lib.mac_internal_place.call_count == call_count + 1

    internal.y = 20
    assert internal.y == 20
    assert lib.mac_internal_place.call_count == call_count + 2

    internal.width = 200
    assert internal.width == 200
    assert lib.mac_internal_place.call_count == call_count + 3

    internal.height = 100
    assert internal.height == 100
    assert lib.mac_internal_place.call_count == call_count + 4
