import sys
from pathlib import Path

import pytest

import libqtile.config
import libqtile.layout
import libqtile.widget
from libqtile.confreader import Config
from test.helpers import Retry
from test.layouts.layout_utils import assert_focus_path, assert_focused


def spawn_cmd(title):
    script = Path(__file__).parent / "scripts" / "window.py"
    cmd = f"{sys.executable} {script.as_posix()} --name TestWindow {title} normal"
    return cmd


class ScratchPadBaseConfig(Config):
    auto_fullscreen = True
    screens = []
    groups = [
        libqtile.config.ScratchPad(
            "SCRATCHPAD",
            dropdowns=[
                libqtile.config.DropDown("dd-a", spawn_cmd("dd-a"), on_focus_lost_hide=False),
                libqtile.config.DropDown("dd-b", spawn_cmd("dd-b"), on_focus_lost_hide=False),
                libqtile.config.DropDown("dd-c", spawn_cmd("dd-c"), on_focus_lost_hide=True),
                libqtile.config.DropDown("dd-d", spawn_cmd("dd-d"), on_focus_lost_hide=True),
                libqtile.config.DropDown(
                    "dd-e",
                    spawn_cmd("dd-e"),
                    match=libqtile.config.Match(title="dd-e"),
                    on_focus_lost_hide=False,
                ),
            ],
        ),
        libqtile.config.ScratchPad(
            "SINGLE_SCRATCHPAD",
            dropdowns=[
                libqtile.config.DropDown("dd-e", spawn_cmd("dd-e"), on_focus_lost_hide=False),
                libqtile.config.DropDown("dd-f", spawn_cmd("dd-f"), on_focus_lost_hide=False),
            ],
            single=True,
        ),
        libqtile.config.ScratchPad(
            "GEOMETRY_SCRATCHPAD",
            dropdowns=[
                libqtile.config.DropDown(
                    "dd-a", spawn_cmd("dd-a"), x=0.2, y=0.2, width=0.6, height=0.6
                ),
                libqtile.config.DropDown(
                    "dd-b", spawn_cmd("dd-b"), x=0.2, y=0.2, width=0.6, height=0.6
                ),
            ],
        ),
        libqtile.config.Group("a"),
        libqtile.config.Group("b"),
    ]
    layouts = [libqtile.layout.max.Max()]
    floating_layout = libqtile.resources.default_config.floating_layout
    keys = []
    mouse = []


scratchpad_config = pytest.mark.parametrize("manager", [ScratchPadBaseConfig], indirect=True)


@Retry(ignore_exceptions=(KeyError,))
def is_spawned(manager, name, scratch_group="SCRATCHPAD"):
    manager.c.group[scratch_group].dropdown_info(name)["window"]
    return True


@Retry(ignore_exceptions=(ValueError,))
def is_killed(manager, name):
    if "window" not in manager.c.group["SCRATCHPAD"].dropdown_info(name):
        return True
    raise ValueError("not yet killed")


@scratchpad_config
def test_sratchpad_with_matcher(manager):
    # adjust command for current display
    manager.c.group["SCRATCHPAD"].dropdown_reconfigure("dd-e")

    manager.test_window("one")
    assert manager.c.group["a"].info()["windows"] == ["one"]

    # First toggling: wait for window
    manager.c.group["SCRATCHPAD"].dropdown_toggle("dd-e")
    is_spawned(manager, "dd-e")

    # assert window in current group "a"
    assert sorted(manager.c.group["a"].info()["windows"]) == ["dd-e", "one"]
    assert_focused(manager, "dd-e")

    # toggle again --> "hide" dd-e
    manager.c.group["SCRATCHPAD"].dropdown_toggle("dd-e")
    assert manager.c.group["a"].info()["windows"] == ["one"]
    assert_focused(manager, "one")
    assert manager.c.group["SCRATCHPAD"].info()["windows"] == ["dd-e"]

    # toggle again --> show again
    manager.c.group["SCRATCHPAD"].dropdown_toggle("dd-e")
    assert sorted(manager.c.group["a"].info()["windows"]) == ["dd-e", "one"]
    assert_focused(manager, "dd-e")
    assert manager.c.group["SCRATCHPAD"].info()["windows"] == []


@scratchpad_config
def test_toggling_single(manager):
    # adjust command for current display
    manager.c.group["SINGLE_SCRATCHPAD"].dropdown_reconfigure("dd-e")
    manager.c.group["SINGLE_SCRATCHPAD"].dropdown_reconfigure("dd-f")
    manager.c.group["SINGLE_SCRATCHPAD"].dropdown_reconfigure("dd-g")
    manager.c.group["SINGLE_SCRATCHPAD"].dropdown_reconfigure("dd-h")

    manager.test_window("one")
    assert manager.c.group["a"].info()["windows"] == ["one"]

    # First toggling: wait for window
    manager.c.group["SINGLE_SCRATCHPAD"].dropdown_toggle("dd-e")
    is_spawned(manager, "dd-e", "SINGLE_SCRATCHPAD")

    # assert window in current group "a"
    assert sorted(manager.c.group["a"].info()["windows"]) == ["dd-e", "one"]
    assert_focused(manager, "dd-e")

    # toggle another window, this should hide the previous one.
    manager.c.group["SINGLE_SCRATCHPAD"].dropdown_toggle("dd-f")
    is_spawned(manager, "dd-f", "SINGLE_SCRATCHPAD")
    assert sorted(manager.c.group["a"].info()["windows"]) == ["dd-f", "one"]
    assert_focused(manager, "dd-f")
    assert manager.c.group["SINGLE_SCRATCHPAD"].info()["windows"] == ["dd-e"]

    # toggle the scratchpad that is now visible.
    manager.c.group["SINGLE_SCRATCHPAD"].dropdown_toggle("dd-f")
    assert sorted(manager.c.group["a"].info()["windows"]) == ["one"]
    assert_focused(manager, "one")
    assert sorted(manager.c.group["SINGLE_SCRATCHPAD"].info()["windows"]) == ["dd-e", "dd-f"]


@scratchpad_config
def test_toggling(manager):
    manager.c.group["SCRATCHPAD"].dropdown_reconfigure("dd-a")

    manager.test_window("one")
    assert manager.c.group["a"].info()["windows"] == ["one"]

    # First toggling: wait for window
    manager.c.group["SCRATCHPAD"].dropdown_toggle("dd-a")
    is_spawned(manager, "dd-a")

    # assert window in current group "a"
    assert sorted(manager.c.group["a"].info()["windows"]) == ["dd-a", "one"]
    assert_focused(manager, "dd-a")

    # toggle again --> "hide" window in scratchpad group
    manager.c.group["SCRATCHPAD"].dropdown_toggle("dd-a")
    assert manager.c.group["a"].info()["windows"] == ["one"]
    assert_focused(manager, "one")
    assert manager.c.group["SCRATCHPAD"].info()["windows"] == ["dd-a"]

    # toggle again --> show again
    manager.c.group["SCRATCHPAD"].dropdown_toggle("dd-a")
    assert sorted(manager.c.group["a"].info()["windows"]) == ["dd-a", "one"]
    assert_focused(manager, "dd-a")
    assert manager.c.group["SCRATCHPAD"].info()["windows"] == []


@scratchpad_config
def test_focus_cycle(manager):
    manager.c.group["SCRATCHPAD"].dropdown_reconfigure("dd-a")
    manager.c.group["SCRATCHPAD"].dropdown_reconfigure("dd-b")

    manager.test_window("one")
    # spawn dd-a by toggling
    assert_focused(manager, "one")

    manager.c.group["SCRATCHPAD"].dropdown_toggle("dd-a")
    is_spawned(manager, "dd-a")
    assert_focused(manager, "dd-a")

    manager.test_window("two")
    assert_focused(manager, "two")

    # spawn dd-b by toggling
    manager.c.group["SCRATCHPAD"].dropdown_toggle("dd-b")
    is_spawned(manager, "dd-b")
    assert_focused(manager, "dd-b")

    # check all windows
    assert sorted(manager.c.group["a"].info()["windows"]) == ["dd-a", "dd-b", "one", "two"]

    assert_focus_path(manager, "one", "two", "dd-a", "dd-b")


@scratchpad_config
def test_focus_lost_hide(manager):
    manager.c.group["SCRATCHPAD"].dropdown_reconfigure("dd-c")
    manager.c.group["SCRATCHPAD"].dropdown_reconfigure("dd-d")

    manager.test_window("one")
    assert_focused(manager, "one")

    # spawn dd-c by toggling
    manager.c.group["SCRATCHPAD"].dropdown_toggle("dd-c")
    is_spawned(manager, "dd-c")
    assert_focused(manager, "dd-c")
    assert sorted(manager.c.group["a"].info()["windows"]) == ["dd-c", "one"]

    # New Window with Focus --> hide current DropDown
    manager.test_window("two")
    assert_focused(manager, "two")
    assert sorted(manager.c.group["a"].info()["windows"]) == ["one", "two"]
    assert sorted(manager.c.group["SCRATCHPAD"].info()["windows"]) == ["dd-c"]

    # spawn dd-b by toggling
    manager.c.group["SCRATCHPAD"].dropdown_toggle("dd-d")
    is_spawned(manager, "dd-d")
    assert_focused(manager, "dd-d")

    assert sorted(manager.c.group["a"].info()["windows"]) == ["dd-d", "one", "two"]
    assert sorted(manager.c.group["SCRATCHPAD"].info()["windows"]) == ["dd-c"]

    # focus next, is the first tiled window --> "hide" dd-d
    manager.c.group.next_window()
    assert_focused(manager, "one")
    assert sorted(manager.c.group["a"].info()["windows"]) == ["one", "two"]
    assert sorted(manager.c.group["SCRATCHPAD"].info()["windows"]) == ["dd-c", "dd-d"]

    # Bring dd-c to front
    manager.c.group["SCRATCHPAD"].dropdown_toggle("dd-c")
    assert_focused(manager, "dd-c")
    assert sorted(manager.c.group["a"].info()["windows"]) == ["dd-c", "one", "two"]
    assert sorted(manager.c.group["SCRATCHPAD"].info()["windows"]) == ["dd-d"]

    # Bring dd-d to front --> "hide dd-c
    manager.c.group["SCRATCHPAD"].dropdown_toggle("dd-d")
    assert_focused(manager, "dd-d")
    assert sorted(manager.c.group["a"].info()["windows"]) == ["dd-d", "one", "two"]
    assert sorted(manager.c.group["SCRATCHPAD"].info()["windows"]) == ["dd-c"]

    # change current group to "b" hids DropDowns
    manager.c.group["b"].toscreen()
    assert sorted(manager.c.group["a"].info()["windows"]) == ["one", "two"]
    assert sorted(manager.c.group["SCRATCHPAD"].info()["windows"]) == ["dd-c", "dd-d"]


@scratchpad_config
def test_kill(manager):
    manager.c.group["SCRATCHPAD"].dropdown_reconfigure("dd-a")

    manager.test_window("one")
    assert_focused(manager, "one")

    # dd-a has no window associated yet
    assert "window" not in manager.c.group["SCRATCHPAD"].dropdown_info("dd-a")

    # First toggling: wait for window
    manager.c.group["SCRATCHPAD"].dropdown_toggle("dd-a")
    is_spawned(manager, "dd-a")
    assert_focused(manager, "dd-a")
    assert manager.c.group["SCRATCHPAD"].dropdown_info("dd-a")["window"]["name"] == "dd-a"

    # kill current window "dd-a"
    manager.c.window.kill()
    manager.c.sync()
    is_killed(manager, "dd-a")
    assert_focused(manager, "one")
    assert "window" not in manager.c.group["SCRATCHPAD"].dropdown_info("dd-a")


@scratchpad_config
def test_floating_toggle(manager):
    manager.c.group["SCRATCHPAD"].dropdown_reconfigure("dd-a")

    manager.test_window("one")
    assert_focused(manager, "one")

    # dd-a has no window associated yet
    assert "window" not in manager.c.group["SCRATCHPAD"].dropdown_info("dd-a")
    # First toggling: wait for window
    manager.c.group["SCRATCHPAD"].dropdown_toggle("dd-a")
    is_spawned(manager, "dd-a")
    assert_focused(manager, "dd-a")

    assert "window" in manager.c.group["SCRATCHPAD"].dropdown_info("dd-a")
    assert sorted(manager.c.group["a"].info()["windows"]) == ["dd-a", "one"]

    manager.c.window.toggle_floating()
    # dd-a has no window associated any more, but is still in group
    assert "window" not in manager.c.group["SCRATCHPAD"].dropdown_info("dd-a")
    assert sorted(manager.c.group["a"].info()["windows"]) == ["dd-a", "one"]

    manager.c.group["SCRATCHPAD"].dropdown_toggle("dd-a")
    is_spawned(manager, "dd-a")
    assert sorted(manager.c.group["a"].info()["windows"]) == ["dd-a", "dd-a", "one"]


@scratchpad_config
def test_stepping_between_groups_should_skip_scratchpads(manager):
    # we are on a group
    manager.c.screen.next_group()
    # we are on b group
    manager.c.screen.next_group()
    # we should be on a group
    assert manager.c.group.info()["name"] == "a"

    manager.c.screen.prev_group()
    # we should be on b group
    assert manager.c.group.info()["name"] == "b"


@scratchpad_config
def test_skip_taskbar(manager):
    manager.c.group["SCRATCHPAD"].dropdown_reconfigure("dd-a")

    manager.test_window("one")
    assert_focused(manager, "one")

    # dd-a has no window associated yet
    assert "window" not in manager.c.group["SCRATCHPAD"].dropdown_info("dd-a")

    # First toggling: wait for window
    manager.c.group["SCRATCHPAD"].dropdown_toggle("dd-a")
    is_spawned(manager, "dd-a")
    assert_focused(manager, "dd-a")
    assert manager.c.group["SCRATCHPAD"].dropdown_info("dd-a")["window"]["name"] == "dd-a"

    if manager.c.core.info()["backend"] == "x11":
        # check that window's _NET_WM_STATE contains _NET_WM_STATE_SKIP_TASKBAR
        net_wm_state = manager.c.window.eval("self.window.get_net_wm_state()")
        assert "_NET_WM_STATE_SKIP_TASKBAR" in net_wm_state


@scratchpad_config
def test_geometry(manager):
    def assert_geometry(x, y, w, h):
        info = manager.c.window.info()
        assert (x, y, w, h) == (info["x"], info["y"], info["width"], info["height"])

    def move_and_resize():
        manager.c.window.set_size_floating(200, 200)
        manager.c.window.set_position_floating(10, 10)

    scratch = manager.c.group["GEOMETRY_SCRATCHPAD"]

    # dd-a spawns with its configured geometry
    scratch.dropdown_toggle("dd-a")
    is_spawned(manager, "dd-a", "GEOMETRY_SCRATCHPAD")
    assert_geometry(160, 120, 478, 358)
    move_and_resize()
    assert_geometry(10, 10, 200, 200)

    # Geometry changes persist across hide/show
    scratch.dropdown_toggle("dd-a")
    scratch.dropdown_toggle("dd-a")
    assert_geometry(10, 10, 200, 200)

    scratch.dropdown_toggle("dd-a")

    # dd-b's geometry is tracked independently: it still spawns at its
    # configured position even though dd-a was moved
    scratch.dropdown_toggle("dd-b")
    is_spawned(manager, "dd-b", "GEOMETRY_SCRATCHPAD")
    assert_geometry(160, 120, 478, 358)
    move_and_resize()
    assert_geometry(10, 10, 200, 200)

    # Geometry changes persist across hide/show
    scratch.dropdown_toggle("dd-b")
    scratch.dropdown_toggle("dd-b")
    assert_geometry(10, 10, 200, 200)
