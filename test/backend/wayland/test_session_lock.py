from types import MethodType

import pytest

from libqtile.backend.wayland._ffi import lib
from libqtile.command.base import CommandError
from test.conftest import dualmonitor


class LockState:
    """Maps server lock status flags."""

    LOCKED = lib.QW_SESSION_LOCK_LOCKED
    UNLOCKED = lib.QW_SESSION_LOCK_UNLOCKED
    CRASHED = lib.QW_SESSION_LOCK_CRASHED


# Functions for finding/navigating LAYER_LOCK


def find_layer_lock(stacking_info):
    """Recursively search the nested stacking tree for the LAYER_LOCK node."""
    if not isinstance(stacking_info, dict):
        return None

    # Check current node
    if stacking_info.get("name") == "LAYER_LOCK":
        return stacking_info

    # Recurse through children
    for child in stacking_info.get("children", []):
        result = find_layer_lock(child)
        if result is not None:
            return result

    return None


def find_node_at_position(node, node_type, x, y, parent_x=0, parent_y=0):
    """
    Looks for a node at given position but, as tree nodes are relative,
    we need to track absolute position of child node.
    """
    if not isinstance(node, dict):
        return False

    abs_x = parent_x + node["x"]
    abs_y = parent_y + node["y"]

    if node["type"] == node_type:
        return abs_x == x and abs_y == y

    for child in node.get("children", []):
        result = find_node_at_position(
            child,
            node_type,
            x,
            y,
            abs_x,
            abs_y,
        )
        if result:
            return True

    return False


def count_node_types(node, counts=None):
    """Returns dict of the number of each node type in a given node."""
    if counts is None:
        counts = {}

    if not isinstance(node, dict):
        return counts

    # Count current node type
    node_type = node.get("type")
    if node_type:
        counts[node_type] = counts.get(node_type, 0) + 1

    # Recurse through children
    for child in node.get("children", []):
        count_node_types(child, counts)

    return counts


@pytest.fixture
def ipc_enable(request):
    """Convenience fixture to enable IPC when locked."""
    yield getattr(request, "param", False)


enable_ipc = pytest.mark.parametrize("ipc_enable", [True], indirect=True)


@pytest.fixture
def lock_manager(wmanager, ipc_enable):
    """Modified manager instance with additional methods to test session lock."""

    def remove_hooks(self) -> None:
        self.c.eval("del hook.subscriptions['qtile']['locked']")
        self.c.eval("del hook.subscriptions['qtile']['unlocked']")

    def _lock_state(self) -> int:
        return int(self.c.core.eval("self.qw.lock_state"))

    def assert_locked(self) -> None:
        assert self._lock_state() == LockState.LOCKED

    def assert_unlocked(self) -> None:
        assert self._lock_state() == LockState.UNLOCKED

    def assert_crashed(self) -> None:
        assert self._lock_state() == LockState.CRASHED

    def _get_layer_lock(self) -> dict:
        info = self.c.core.stacking_info()
        layer = find_layer_lock(info)
        assert layer
        return layer

    def assert_layer_lock_enabled(self, enabled):
        assert self._get_layer_lock()["enabled"] == enabled

    def assert_rect_at_position(self, x, y):
        layer = self._get_layer_lock()
        assert find_node_at_position(layer, "rect", x, y)

    def assert_buffer_at_position(self, x, y):
        layer = self._get_layer_lock()
        assert find_node_at_position(layer, "buffer", x, y)

    def assert_rect_count(self, num):
        layer = self._get_layer_lock()
        counts = count_node_types(layer)
        assert counts.get("rect", 0) == num

    def assert_buffer_count(self, num):
        layer = self._get_layer_lock()
        counts = count_node_types(layer)
        assert counts.get("buffer", 0) == num

    # bind methods to our manager instance
    for f in [
        remove_hooks,
        _lock_state,
        assert_locked,
        assert_unlocked,
        assert_crashed,
        _get_layer_lock,
        assert_layer_lock_enabled,
        assert_rect_at_position,
        assert_buffer_at_position,
        assert_rect_count,
        assert_buffer_count,
    ]:
        setattr(wmanager, f.__name__, MethodType(f, wmanager))

    # When the session is locked, IPC is disabled by default.
    # However, for testing, we need access to the internals so we
    # re-enable IPC by removing the hooks in the server.
    if ipc_enable:
        wmanager.remove_hooks()

    yield wmanager


# Parameterise every test with the session-lock client
pytestmark = pytest.mark.parametrize("test_client", ["session-lock"], indirect=True)


@enable_ipc
def test_session_lock_server(lock_manager, test_client):
    """Basic test of locked state."""
    # Session is unlocked so layer lock is disabled
    lock_manager.assert_layer_lock_enabled(False)

    # Lock then client and verify lock state and layer_lock state
    test_client.assert_ok("lock")
    lock_manager.assert_locked()
    lock_manager.assert_layer_lock_enabled(True)

    # Check state is reset after unlock
    test_client.assert_ok("unlock")
    lock_manager.assert_unlocked()
    lock_manager.assert_layer_lock_enabled(False)


def test_session_lock_client(lock_manager, test_client):
    """Check that correct messages are sent to clients."""
    test_client.assert_ok("lock")
    test_client.assert_ok("check_locked")

    test_client.assert_ok("unlock")
    test_client.assert_ok("check_unlocked")


def test_ipc_disabled(lock_manager, test_client):
    """
    Confirm IPC is unavailable when locked and re-enabled when lock is removed.
    """
    test_client.assert_ok("lock")
    with pytest.raises(CommandError):
        lock_manager.assert_locked()

    # Unlocking should re-enable IPC
    test_client.assert_ok("unlock")
    lock_manager.assert_unlocked()


@enable_ipc
def test_crashed(lock_manager, test_client):
    """Confirm crashed state is still locked."""
    test_client.assert_ok("lock")
    lock_manager.assert_layer_lock_enabled(True)

    test_client.assert_ok("crash")
    lock_manager.assert_crashed()
    lock_manager.assert_layer_lock_enabled(True)

    test_client.restart()
    test_client.assert_error("lock", "compositor rejected lock")
    test_client.assert_error("unlock", "no active lock")


def test_crashed_ipc_disabled(lock_manager, test_client):
    """Confirm IPC is still locked when in crashed state."""
    test_client.assert_ok("lock")
    test_client.assert_ok("crash")
    with pytest.raises(CommandError):
        lock_manager.assert_crashed()


@enable_ipc
def test_multiple_lock_requests(lock_manager, test_client):
    """Multiple requests for a lock should be rejected."""
    test_client.assert_ok("lock")
    lock_manager.assert_locked()

    test_client.assert_error("lock", "already holding a lock object")
    lock_manager.assert_locked()

    test_client.assert_ok("unlock")
    lock_manager.assert_unlocked()


@enable_ipc
def test_lock_surface_single(lock_manager, test_client):
    """Check that lock surface is added to LAYER_LOCK."""
    lock_manager.assert_rect_count(1)
    lock_manager.assert_rect_at_position(0, 0)

    lock_manager.assert_buffer_count(0)

    test_client.assert_ok("lock")
    test_client.assert_ok("create_surface")
    test_client.assert_ok("check_surface_count 1")

    lock_manager.assert_buffer_count(1)
    lock_manager.assert_buffer_at_position(0, 0)

    test_client.assert_ok("unlock")
    lock_manager.assert_buffer_count(0)


@dualmonitor
@enable_ipc
def test_lock_surface_dualmonito(lock_manager, test_client):
    """
    Check that lock surfaces are added to LAYER_LOCK and
    positioned correctly on multiple monitors.
    """
    lock_manager.assert_rect_count(2)
    lock_manager.assert_rect_at_position(0, 0)
    lock_manager.assert_rect_at_position(800, 0)

    lock_manager.assert_buffer_count(0)

    test_client.assert_ok("lock")
    test_client.assert_ok("create_surface")
    test_client.assert_ok("check_surface_count 2")

    lock_manager.assert_buffer_count(2)
    lock_manager.assert_buffer_at_position(0, 0)
    lock_manager.assert_buffer_at_position(800, 0)

    test_client.assert_ok("unlock")
    lock_manager.assert_buffer_count(0)
