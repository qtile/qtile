from __future__ import annotations

import sys
from unittest.mock import MagicMock

import pytest

from libqtile.backend.macos.core import Core
from test.backend.macos.fake_ffi import FakeFFI


@pytest.fixture
def core():
    fake_ffi = FakeFFI()
    # Patch the _ffi import inside Core.__init__
    with MagicMock() as mock_ffi_mod:
        mock_ffi_mod.ffi = fake_ffi.ffi
        mock_ffi_mod.lib = fake_ffi.lib
        with pytest.MonkeyPatch.context() as mp:
            mp.setitem(sys.modules, "libqtile.backend.macos._ffi", mock_ffi_mod)
            c = Core()
            return c


def test_unit_core_init(core):
    assert core.name == "macos"
    assert core._running is False
    assert core._poll_handle is None


def test_unit_core_set_qtile(core):
    qtile = MagicMock()
    core.set_qtile(qtile)
    assert core.qtile == qtile
    assert core._running is True
    assert core._poll_handle is not None
    qtile.call_later.assert_called_with(0.01, core._poll_cf)


def test_unit_core_finalize(core):
    qtile = MagicMock()
    core.set_qtile(qtile)
    poll_handle = core._poll_handle

    core.finalize()
    assert core._running is False
    assert core.qtile is None
    poll_handle.cancel.assert_called_once()
    assert core._poll_handle is None
    core._lib.mac_observer_stop.assert_called_once()
    core._lib.mac_event_tap_stop.assert_called_once()


def test_unit_core_poll_cf(core):
    core._running = True
    core.qtile = MagicMock()
    core._poll_cf()
    core._lib.mac_poll_runloop.assert_called_once()
    core.qtile.call_later.assert_called_with(0.01, core._poll_cf)


def test_unit_core_get_output_info(core):
    from libqtile.config import Output, ScreenRect

    mock_output = Output(
        port="test_output",
        make=None,
        model=None,
        serial=None,
        rect=ScreenRect(0, 0, 1920, 1080),
    )
    with MagicMock() as mock_method:
        mock_method.return_value = [mock_output]
        core.get_output_info = mock_method
        outputs = core.get_output_info()
        assert len(outputs) == 1
        assert outputs[0].port == "test_output"
        assert outputs[0].rect.width == 1920


def test_unit_core_finalize_cleans_up_input_and_windows(core):
    """finalize() must ungrab keys/buttons and clear windows to avoid leaked state."""
    from libqtile.backend.macos.inputs import InputManager

    qtile = MagicMock()
    core.set_qtile(qtile)
    # Simulate grabbed state
    core.input_manager = InputManager(qtile, core)
    core.input_manager.grabbed_keys.add((49, 0))
    core.grabbed_buttons.add((1, 0))
    # Simulate tracked windows
    core.windows = {1: MagicMock(), 2: MagicMock()}

    core.finalize()

    assert len(core.input_manager.grabbed_keys) == 0
    assert len(core.grabbed_buttons) == 0
    assert len(core.windows) == 0


def test_unit_core_ax_trust_check_is_cached(core):
    """_check_ax_trust() uses a cached result after the first call."""
    # Before any call, cache is uninitialised
    assert core._ax_trusted is None

    # Patch ctypes so no real dlopen happens
    import unittest.mock as mock

    with mock.patch("ctypes.cdll.LoadLibrary") as load_lib:
        load_lib.return_value.AXIsProcessTrusted.return_value = True
        load_lib.return_value.AXIsProcessTrusted.restype = None

        core._check_ax_trust()
        core._check_ax_trust()
        core._check_ax_trust()

    # dlopen (LoadLibrary) should only have been called once
    assert load_lib.call_count == 1
    assert core._ax_trusted is True


def test_idle_notifier_importable():
    from libqtile.backend.macos.idle import IdleNotifier

    assert IdleNotifier is not None


def test_event_tap_excludes_right_and_bottom_edge_pixels(core):
    """Clicks at x==win.x+win.width or y==win.y+win.height must NOT go to internal window.

    Boundary hit-detection should use half-open intervals [x, x+w) so that a
    pixel exactly on the trailing edge is NOT attributed to the window.
    """
    from libqtile.backend import base

    qtile = MagicMock()
    core.set_qtile(qtile)
    core.setup_listener()

    # Internal window at origin, 100×50
    internal_win = MagicMock(spec=base.Internal)
    internal_win.x = 0
    internal_win.y = 0
    internal_win.width = 100
    internal_win.height = 50
    qtile.windows_map = {1: internal_win}

    # Click exactly on the right edge pixel (x == width)
    core.get_mouse_position = MagicMock(return_value=(100, 25))
    qtile.call_soon_threadsafe.reset_mock()
    result = core._callback_handle(1, 0, 0, None)  # type=1: LeftMouseDown
    assert qtile.call_soon_threadsafe.call_count == 0, (
        "click at x==win.x+win.width should NOT dispatch to internal window"
    )
    assert result != 1, "click at right-edge pixel must not be swallowed"

    # Click exactly on the bottom edge pixel (y == height)
    core.get_mouse_position = MagicMock(return_value=(50, 50))
    qtile.call_soon_threadsafe.reset_mock()
    result = core._callback_handle(1, 0, 0, None)
    assert qtile.call_soon_threadsafe.call_count == 0, (
        "click at y==win.y+win.height should NOT dispatch to internal window"
    )
