import pytest

from libqtile import widget
from libqtile.backend.base.idle_notify import IdleNotifier
from libqtile.bar import Bar
from libqtile.config import IdleTimer, Screen
from libqtile.confreader import Config
from libqtile.lazy import lazy
from test.helpers import Retry


def no_op():
    pass


class FakeQtile:
    locked = False


class FakeCore:
    qtile = FakeQtile()

    @property
    def inhibited(self):
        if not hasattr(self, "_inhibited"):
            self._inhibited = False

    @inhibited.setter
    def inhibited(self, value):
        self._inhibited = value


class IdleConfig(Config):
    idle_timers = [
        IdleTimer(
            1,
            action=lazy.widget["textbox"].update("fired"),
            resume=lazy.widget["textbox"].update("resumed"),
        ),
        IdleTimer(1, action=lazy.group["2"].toscreen(), respect_inhibitor=False),
    ]

    screens = [Screen(top=Bar([widget.TextBox("unset")], 20))]


idle_config = pytest.mark.parametrize("manager", [IdleConfig], indirect=True)


@Retry(ignore_exceptions=(AssertionError,))
def wait_for_text(manager, text):
    assert manager.c.widget["textbox"].info()["text"] == text


@Retry(ignore_exceptions=(AssertionError,))
def wait_for_group(manager, group_name):
    assert manager.c.group.info()["name"] == group_name


# Only one timer is set for each interval so duplicates are not add to list of timeouts
# timeouts should also be in ascending order
@pytest.mark.parametrize(
    "timers,expected_output",
    [
        ([IdleTimer(1, no_op), IdleTimer(2, no_op)], [1, 2]),
        ([IdleTimer(2, no_op), IdleTimer(1, no_op)], [1, 2]),
        ([IdleTimer(2, no_op), IdleTimer(1, no_op), IdleTimer(2, no_op)], [1, 2]),
    ],
)
def test_timer_sorting(timers, expected_output):
    idle_notifier = IdleNotifier(FakeCore)
    idle_notifier.add_timers(timers)
    assert idle_notifier.timeouts == expected_output


@idle_config
def test_idle_timer(manager):
    wait_for_text(manager, "fired")

    # Force resume event
    manager.c.core.eval("self.idle_notifier.fire_resume()")
    wait_for_text(manager, "resumed")


@idle_config
def test_idle_timer_inhibited(manager):
    """Test timer is not fired when inhibitor in place."""

    # Reset initial state in case timer was fired too early
    manager.c.core.eval("self.idle_notifier.reset()")
    manager.c.group["1"].toscreen()
    manager.c.widget["textbox"].update("unset")

    manager.c.core.set_idle_inhibitor()
    # The group change timer is set to ignore the inhibitor...
    wait_for_group(manager, "2")
    # ... but the textbox respects it
    assert manager.c.widget["textbox"].info()["text"] == "unset"
