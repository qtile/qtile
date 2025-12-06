import pytest

from libqtile.backend.wayland.idle_inhibit import InhibitorManager
from libqtile.config import IdleInhibitor, Match
from libqtile.confreader import Config
from test.helpers import Retry


class FakeCore:
    class FakeQtile:
        locked = False

    def no_op(*args, **kwargs):
        pass

    qtile = FakeQtile()
    set_inhibited = no_op


class InhibitorConfig(Config):
    idle_inhibitors = [
        IdleInhibitor(when="fullscreen"),  # Any fullscreen window
        IdleInhibitor(match=Match(title="One"), when="focus"),
        IdleInhibitor(match=Match(title="Two"), when="visible"),
        IdleInhibitor(match=Match(title="Three"), when="open"),
    ]


inhibitor_config = pytest.mark.parametrize("manager", [InhibitorConfig], indirect=True)


def is_inhibited(manager):
    return len(manager.c.core.get_idle_inhibitors(active_only=True)) > 0


@Retry(ignore_exceptions=(AssertionError,))
def wait_for_windows(manager, count):
    assert len(manager.c.windows()) == count


def test_inhibitor_manager():
    manager = InhibitorManager(FakeCore())

    manager.add_window_inhibitor(1, "open")
    assert len(manager.inhibitors) == 1

    # Same window, different method
    manager.add_window_inhibitor(1, "fullscreen")
    assert len(manager.inhibitors) == 2

    # Different window
    manager.add_window_inhibitor(2, "fullscreen")
    assert len(manager.inhibitors) == 3

    # Existing window + method combination
    manager.add_window_inhibitor(1, "fullscreen")
    assert len(manager.inhibitors) == 3

    manager.add_window_inhibitor(4, "open")
    assert len(manager.inhibitors) == 4

    # The inhibitor list is sorted first so inhibitors that always return True (e.g. "open")
    # are checked first
    sorted_methods = [o.inhibitor_type.name for o in manager.inhibitors]
    assert sorted_methods == ["OPEN", "OPEN", "FULLSCREEN", "FULLSCREEN"]


@inhibitor_config
def test_inhibitor_open(manager):
    assert not is_inhibited(manager)

    manager.test_window("NotThree")
    wait_for_windows(manager, 1)
    assert not is_inhibited(manager)

    manager.test_window("Three")
    wait_for_windows(manager, 2)
    assert is_inhibited(manager)

    manager.c.window.kill()
    wait_for_windows(manager, 1)
    assert not is_inhibited(manager)


@inhibitor_config
def test_inhibitor_visible(manager):
    assert not is_inhibited(manager)

    manager.test_window("One")
    wait_for_windows(manager, 1)
    assert is_inhibited(manager)

    # Window is now on a different group
    manager.c.screen.next_group()
    assert not is_inhibited(manager)

    # Window is visible again
    manager.c.screen.prev_group()
    assert is_inhibited(manager)


@inhibitor_config
def test_inhibitor_focus(manager):
    assert not is_inhibited(manager)

    manager.test_window("One")
    wait_for_windows(manager, 1)
    assert is_inhibited(manager)

    # Window NotOne should be focused
    manager.test_window("NotOne")
    wait_for_windows(manager, 2)
    assert not is_inhibited(manager)

    manager.c.group.prev_window()
    assert is_inhibited(manager)


@inhibitor_config
def test_inhibitor_fullscreen(manager):
    assert not is_inhibited(manager)

    manager.test_window("Four")
    wait_for_windows(manager, 1)
    assert not is_inhibited(manager)

    manager.c.window.toggle_fullscreen()
    assert is_inhibited(manager)

    manager.c.window.toggle_fullscreen()
    assert not is_inhibited(manager)


@inhibitor_config
def test_inhibitor_global(manager):
    assert not is_inhibited(manager)

    manager.c.core.set_idle_inhibitor()
    assert is_inhibited(manager)

    manager.c.core.remove_idle_inhibitor()
    assert not is_inhibited(manager)
