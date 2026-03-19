from __future__ import annotations

import unittest.mock as mock


class FakeLib:
    """Stub for the CFFI lib object. Every ``lib.*`` call used in the backend has an
    explicit stub here returning a sensible default so tests never hit real C code."""

    def __init__(self):
        # Initialisation
        self.mac_init_app = mock.MagicMock(return_value=None)

        # Integer / bool stubs
        self.mac_get_idle_time = mock.MagicMock(return_value=0.0)
        self.mac_observer_start = mock.MagicMock(return_value=0)
        self.mac_observer_stop = mock.MagicMock(return_value=None)
        self.mac_event_tap_start = mock.MagicMock(return_value=0)
        self.mac_event_tap_stop = mock.MagicMock(return_value=None)
        self.mac_get_windows = mock.MagicMock(return_value=0)
        self.mac_get_outputs = mock.MagicMock(return_value=0)
        self.mac_free_windows = mock.MagicMock(return_value=None)
        self.mac_free_outputs = mock.MagicMock(return_value=None)
        self.mac_poll_runloop = mock.MagicMock(return_value=None)
        self.mac_warp_pointer = mock.MagicMock(return_value=None)
        self.mac_get_mouse_position = mock.MagicMock(return_value=None)
        self.mac_simulate_keypress = mock.MagicMock(return_value=None)
        self.mac_is_window = mock.MagicMock(return_value=True)

        # Window stubs
        self.mac_window_retain = mock.MagicMock(return_value=None)
        self.mac_window_release = mock.MagicMock(return_value=None)
        self.mac_window_place = mock.MagicMock(return_value=None)
        self.mac_window_focus = mock.MagicMock(return_value=None)
        self.mac_window_kill = mock.MagicMock(return_value=None)
        self.mac_window_set_hidden = mock.MagicMock(return_value=None)
        self.mac_window_is_visible = mock.MagicMock(return_value=1)
        self.mac_window_bring_to_front = mock.MagicMock(return_value=None)
        self.mac_window_set_fullscreen = mock.MagicMock(return_value=None)
        self.mac_window_set_maximized = mock.MagicMock(return_value=None)
        self.mac_window_set_minimized = mock.MagicMock(return_value=None)
        self.mac_window_get_position = mock.MagicMock(return_value=None)
        self.mac_window_get_size = mock.MagicMock(return_value=None)
        self.mac_window_get_name = mock.MagicMock(return_value=0)  # NULL by default
        self.mac_window_get_app_name = mock.MagicMock(return_value=0)
        self.mac_window_get_bundle_id = mock.MagicMock(return_value=0)
        self.mac_window_get_role = mock.MagicMock(return_value=0)
        self.mac_window_get_parent = mock.MagicMock(return_value=1)  # non-zero = error/no parent
        self.mac_window_get_pid = mock.MagicMock(return_value=0)
        self.mac_get_focused_window = mock.MagicMock(return_value=1)  # non-zero = error

        # Internal window stubs
        self.mac_internal_new = mock.MagicMock(return_value=mock.MagicMock())
        self.mac_internal_free = mock.MagicMock(return_value=None)
        self.mac_internal_place = mock.MagicMock(return_value=None)
        self.mac_internal_set_visible = mock.MagicMock(return_value=None)
        self.mac_internal_bring_to_front = mock.MagicMock(return_value=None)
        self.mac_internal_get_buffer = mock.MagicMock(return_value=0)  # NULL
        self.mac_internal_draw = mock.MagicMock(return_value=None)

        # Memory management
        self.free = mock.MagicMock(return_value=None)


class FakeFfi:
    """Stub for the CFFI ffi object."""

    NULL = 0

    def __init__(self):
        self._new_mocks: dict[str, mock.MagicMock] = {}

    def new(self, type_str: str, init=None) -> mock.MagicMock:
        """Return a MagicMock that supports item assignment and index access."""
        m = mock.MagicMock()
        # Support m[0] returning 0 for int pointer reads
        m.__getitem__ = mock.MagicMock(return_value=0)
        return m

    def cast(self, type_str: str, value) -> int:
        """Return the value cast to int (simplistic but sufficient for uintptr_t casts)."""
        try:
            return int(value)
        except (TypeError, ValueError):
            return 0

    def string(self, ptr) -> bytes:
        """Return empty bytes for NULL, otherwise b''."""
        if ptr == self.NULL:
            return b""
        return b""

    def gc(self, ptr, destructor) -> mock.MagicMock:
        """Register a destructor (no-op in tests)."""
        return ptr

    def callback(self, signature):
        """Decorator stub — just returns the function unchanged."""

        def decorator(fn):
            return fn

        return decorator


def make_fake_ffi() -> tuple[FakeFfi, FakeLib]:
    """Return ``(FakeFfi(), FakeLib())`` for use in unit tests."""
    return FakeFfi(), FakeLib()


# ---------------------------------------------------------------------------
# Legacy shim: keep the old ``FakeFFI`` class working so existing tests
# (test_unit_core.py, test_unit_idle.py) that import it do not break.
# ---------------------------------------------------------------------------
class FakeFFI:
    def __init__(self):
        self.ffi = FakeFfi()
        self.lib = FakeLib()

    def _setup_defaults(self):
        # No-op: FakeFfi and FakeLib already have sensible defaults.
        pass
