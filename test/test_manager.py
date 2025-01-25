# Copyright (c) 2011 Florian Mounier
# Copyright (c) 2011 Anshuman Bhaduri
# Copyright (c) 2012-2014 Tycho Andersen
# Copyright (c) 2013 xarvh
# Copyright (c) 2013 Craig Barnes
# Copyright (c) 2014 Sean Vig
# Copyright (c) 2014 Adi Sieker
# Copyright (c) 2014 Sebastien Blot
# Copyright (c) 2020 Mikel Ward
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import logging
from pathlib import Path

import pytest

import libqtile.bar
import libqtile.config
import libqtile.confreader
import libqtile.hook
import libqtile.layout
import libqtile.widget
from libqtile.command.client import SelectError
from libqtile.command.interface import CommandError, CommandException
from libqtile.config import Match
from libqtile.confreader import Config
from libqtile.group import _Group
from libqtile.lazy import lazy
from test.conftest import dualmonitor, multimonitor
from test.helpers import BareConfig, Retry, assert_window_died
from test.layouts.layout_utils import assert_focused

configs_dir = Path(__file__).resolve().parent / "configs"


class ManagerConfig(Config):
    auto_fullscreen = True
    groups = [
        libqtile.config.Group("a"),
        libqtile.config.Group("b"),
        libqtile.config.Group("c"),
        libqtile.config.Group("d"),
    ]
    layouts = [
        libqtile.layout.stack.Stack(num_stacks=1),
        libqtile.layout.stack.Stack(num_stacks=2),
        libqtile.layout.tile.Tile(ratio=0.5),
        libqtile.layout.max.Max(),
    ]
    floating_layout = libqtile.layout.floating.Floating(
        float_rules=[
            *libqtile.layout.floating.Floating.default_float_rules,
            Match(wm_class="float"),
            Match(title="float"),
        ]
    )
    keys = [
        libqtile.config.Key(
            ["control"],
            "k",
            lazy.layout.up(),
        ),
        libqtile.config.Key(
            ["control"],
            "j",
            lazy.layout.down(),
        ),
    ]
    mouse = []
    screens = [
        libqtile.config.Screen(
            bottom=libqtile.bar.Bar(
                [
                    libqtile.widget.Prompt(),
                    libqtile.widget.GroupBox(),
                ],
                20,
            ),
        )
    ]
    follow_mouse_focus = True
    reconfigure_screens = False


manager_config = pytest.mark.parametrize("manager", [ManagerConfig], indirect=True)


@dualmonitor
@manager_config
def test_screen_dim(manager):
    manager.test_window("one")
    assert manager.c.screen.info()["index"] == 0
    assert manager.c.screen.info()["x"] == 0
    assert manager.c.screen.info()["width"] == 800
    assert manager.c.group.info()["name"] == "a"
    assert manager.c.group.info()["focus"] == "one"

    manager.c.to_screen(1)
    manager.test_window("one")
    assert manager.c.screen.info()["index"] == 1
    assert manager.c.screen.info()["x"] == 800
    assert manager.c.screen.info()["width"] == 640
    assert manager.c.group.info()["name"] == "b"
    assert manager.c.group.info()["focus"] == "one"

    manager.c.to_screen(0)
    assert manager.c.screen.info()["index"] == 0
    assert manager.c.screen.info()["x"] == 0
    assert manager.c.screen.info()["width"] == 800
    assert manager.c.group.info()["name"] == "a"
    assert manager.c.group.info()["focus"] == "one"


@pytest.mark.parametrize("xephyr", [{"xoffset": 0}], indirect=True)
@manager_config
def test_clone_dim(manager):
    manager.test_window("one")
    assert manager.c.screen.info()["index"] == 0
    assert manager.c.screen.info()["x"] == 0
    assert manager.c.screen.info()["width"] == 800
    assert manager.c.group.info()["name"] == "a"
    assert manager.c.group.info()["focus"] == "one"

    assert len(manager.c.get_screens()) == 1


@dualmonitor
@manager_config
def test_to_screen(manager):
    assert manager.c.screen.info()["index"] == 0
    manager.c.to_screen(1)
    assert manager.c.screen.info()["index"] == 1
    manager.test_window("one")
    manager.c.to_screen(0)
    manager.test_window("two")

    ga = manager.c.get_groups()["a"]
    assert ga["windows"] == ["two"]

    gb = manager.c.get_groups()["b"]
    assert gb["windows"] == ["one"]

    assert manager.c.window.info()["name"] == "two"
    manager.c.next_screen()
    assert manager.c.window.info()["name"] == "one"
    manager.c.next_screen()
    assert manager.c.window.info()["name"] == "two"
    manager.c.prev_screen()
    assert manager.c.window.info()["name"] == "one"


@dualmonitor
@manager_config
def test_togroup(manager):
    manager.test_window("one")
    with pytest.raises(CommandError):
        manager.c.window.togroup("nonexistent")
    assert manager.c.get_groups()["a"]["focus"] == "one"

    manager.c.window.togroup("a")
    assert manager.c.get_groups()["a"]["focus"] == "one"

    manager.c.window.togroup("b", switch_group=True)
    assert manager.c.get_groups()["b"]["focus"] == "one"
    assert manager.c.get_groups()["a"]["focus"] is None
    assert manager.c.group.info()["name"] == "b"

    manager.c.window.togroup("a")
    assert manager.c.get_groups()["a"]["focus"] == "one"
    assert manager.c.group.info()["name"] == "b"

    manager.c.to_screen(1)
    manager.c.window.togroup("c")
    assert manager.c.get_groups()["c"]["focus"] == "one"


@manager_config
def test_resize(manager):
    manager.c.screen[0].resize(x=10, y=10, w=100, h=100)

    @Retry(ignore_exceptions=(AssertionError))
    def run():
        d = manager.c.screen[0].info()
        assert d["width"] == 100, "screen did not resize"
        assert d["height"] == 100, "screen did not resize"
        return d

    d = run()
    assert d["x"] == d["y"] == 10


def test_minimal(manager):
    assert manager.c.status() == "OK"


@manager_config
def test_events(manager):
    assert manager.c.status() == "OK"


# FIXME: failing test disabled. For some reason we don't seem
# to have a keymap in Xnest or Xephyr 99% of the time.
@manager_config
def test_keypress(manager):
    manager.test_window("one")
    manager.test_window("two")
    with pytest.raises(CommandError):
        manager.c.simulate_keypress(["unknown"], "j")
    assert manager.c.get_groups()["a"]["focus"] == "two"
    manager.c.simulate_keypress(["control"], "j")
    assert manager.c.get_groups()["a"]["focus"] == "one"


class TooFewGroupsConfig(ManagerConfig):
    groups = []


@pytest.mark.parametrize("manager", [TooFewGroupsConfig], indirect=True)
@multimonitor
def test_too_few_groups(manager):
    assert manager.c.get_groups()
    assert len(manager.c.get_groups()) == len(manager.c.get_screens())


class _ChordsConfig(Config):
    groups = [libqtile.config.Group("a")]
    layouts = [libqtile.layout.max.Max()]
    floating_layout = libqtile.resources.default_config.floating_layout
    keys = [
        libqtile.config.Key(
            [],
            "k",
            lazy.layout.up(),
        ),
        libqtile.config.KeyChord(
            ["control"],
            "a",
            [
                libqtile.config.Key(
                    [],
                    "j",
                    lazy.layout.down(),
                )
            ],
        ),
        libqtile.config.KeyChord(
            ["control"],
            "b",
            [
                libqtile.config.Key(
                    [],
                    "j",
                    lazy.layout.down(),
                )
            ],
            "test",
        ),
        libqtile.config.KeyChord(
            ["control"],
            "d",
            [
                libqtile.config.KeyChord(
                    [],
                    "a",
                    [
                        libqtile.config.KeyChord(
                            [],
                            "1",
                            [
                                libqtile.config.Key([], "u", lazy.ungrab_chord()),
                                libqtile.config.Key([], "v", lazy.ungrab_all_chords()),
                                libqtile.config.Key([], "j", lazy.layout.down()),
                            ],
                            "inner_named",
                        ),
                    ],
                ),
                libqtile.config.Key([], "z", lazy.layout.down()),
            ],
            "nesting_test",
        ),
    ]
    mouse = []
    screens = [
        libqtile.config.Screen(
            bottom=libqtile.bar.Bar(
                [
                    libqtile.widget.GroupBox(),
                ],
                20,
            ),
        )
    ]
    auto_fullscreen = True


chords_config = pytest.mark.parametrize("manager", [_ChordsConfig], indirect=True)


@chords_config
def test_immediate_chord(manager):
    manager.test_window("three")
    manager.test_window("two")
    manager.test_window("one")
    assert manager.c.get_groups()["a"]["focus"] == "one"
    # use normal bind to shift focus up
    manager.c.simulate_keypress([], "k")
    assert manager.c.get_groups()["a"]["focus"] == "two"
    # enter into key chord and "k" binding no longer working
    manager.c.simulate_keypress(["control"], "a")
    manager.c.simulate_keypress([], "k")
    assert manager.c.get_groups()["a"]["focus"] == "two"
    # leave chord using "Escape", "k" bind work again
    manager.c.simulate_keypress([], "Escape")
    manager.c.simulate_keypress([], "k")
    assert manager.c.get_groups()["a"]["focus"] == "three"
    # enter key chord and use it's "j" binding to shift focus down
    manager.c.simulate_keypress(["control"], "a")
    manager.c.simulate_keypress([], "j")
    assert manager.c.get_groups()["a"]["focus"] == "two"
    # in immediate chord we leave it after use any
    # bind from it, "j" bind no longer working
    manager.c.simulate_keypress([], "j")
    assert manager.c.get_groups()["a"]["focus"] == "two"


@chords_config
def test_mode_chord(manager):
    manager.test_window("three")
    manager.test_window("two")
    manager.test_window("one")
    assert manager.c.get_groups()["a"]["focus"] == "one"
    # use normal bind to shift focus up
    manager.c.simulate_keypress([], "k")
    assert manager.c.get_groups()["a"]["focus"] == "two"
    # enter into key chord and "k" binding no longer working
    manager.c.simulate_keypress(["control"], "b")
    manager.c.simulate_keypress([], "k")
    assert manager.c.get_groups()["a"]["focus"] == "two"
    # leave chord using "Escape", "k" bind work again
    manager.c.simulate_keypress([], "Escape")
    manager.c.simulate_keypress([], "k")
    assert manager.c.get_groups()["a"]["focus"] == "three"
    # enter key chord and use it's "j" binding to shift focus down
    manager.c.simulate_keypress(["control"], "b")
    manager.c.simulate_keypress([], "j")
    assert manager.c.get_groups()["a"]["focus"] == "two"
    # in mode chord we __not__ leave it after use any
    # bind from it, "j" bind still working
    manager.c.simulate_keypress([], "j")
    assert manager.c.get_groups()["a"]["focus"] == "one"
    # only way to exit mode chord is by hit "Escape"
    manager.c.simulate_keypress([], "Escape")
    manager.c.simulate_keypress([], "j")
    assert manager.c.get_groups()["a"]["focus"] == "one"


@chords_config
def test_chord_stack(manager):
    manager.test_window("two")
    manager.test_window("one")
    assert manager.c.get_groups()["a"]["focus"] == "one"
    manager.c.simulate_keypress(["control"], "d")  # ["nesting_test"]
    # "z" should work, "k" shouldn't:
    manager.c.simulate_keypress([], "z")
    assert manager.c.get_groups()["a"]["focus"] == "two"
    manager.c.simulate_keypress([], "z")
    assert manager.c.get_groups()["a"]["focus"] == "one"
    manager.c.simulate_keypress([], "k")
    assert manager.c.get_groups()["a"]["focus"] == "one"
    # enter ["nesting_test", "", "inner_named"]:
    manager.c.simulate_keypress([], "a")
    manager.c.simulate_keypress([], "1")
    # "j" should work:
    manager.c.simulate_keypress([], "j")
    assert manager.c.get_groups()["a"]["focus"] == "two"
    manager.c.simulate_keypress([], "j")
    assert manager.c.get_groups()["a"]["focus"] == "one"
    # leave "inner_named" ~> ["nesting_test"]:
    manager.c.simulate_keypress([], "u")
    manager.c.simulate_keypress([], "z")
    assert manager.c.get_groups()["a"]["focus"] == "two"
    manager.c.simulate_keypress([], "z")
    assert manager.c.get_groups()["a"]["focus"] == "one"
    manager.c.simulate_keypress([], "k")
    assert manager.c.get_groups()["a"]["focus"] == "one"
    # enter ["nesting_test", "", "inner_named"]:
    manager.c.simulate_keypress([], "a")
    manager.c.simulate_keypress([], "1")
    # leave all: ~> []
    manager.c.simulate_keypress([], "v")
    # "k" should work, "z" shouldn't:
    manager.c.simulate_keypress([], "k")
    assert manager.c.get_groups()["a"]["focus"] == "two"
    manager.c.simulate_keypress([], "k")
    assert manager.c.get_groups()["a"]["focus"] == "one"
    manager.c.simulate_keypress([], "z")
    assert manager.c.get_groups()["a"]["focus"] == "one"


@manager_config
def test_spawn(manager):
    # Spawn something with a pid greater than init's
    assert int(manager.c.spawn("true")) > 1


@manager_config
def test_spawn_list(manager):
    # Spawn something with a pid greater than init's
    assert int(manager.c.spawn(["echo", "true"])) > 1


@manager_config
def test_kill_window(manager):
    manager.test_window("one")
    window_info = manager.c.window.info()
    manager.c.window[window_info["id"]].kill()
    assert_window_died(manager.c, window_info)


@manager_config
def test_kill_other(manager):
    manager.c.group.setlayout("tile")
    one = manager.test_window("one")
    assert manager.c.window.info()["width"] == 798
    window_one_info = manager.c.window.info()
    assert manager.c.window.info()["height"] == 578
    two = manager.test_window("two")
    assert manager.c.window.info()["name"] == "two"
    assert manager.c.window.info()["width"] == 398
    assert manager.c.window.info()["height"] == 578
    assert len(manager.c.windows()) == 2

    manager.kill_window(one)
    assert_window_died(manager.c, window_one_info)

    assert manager.c.window.info()["name"] == "two"
    assert manager.c.window.info()["width"] == 798
    assert manager.c.window.info()["height"] == 578
    manager.kill_window(two)


@manager_config
def test_regression_groupswitch(manager):
    manager.c.group["c"].toscreen()
    manager.c.group["d"].toscreen()
    assert manager.c.get_groups()["c"]["screen"] is None


@manager_config
def test_next_layout(manager):
    manager.test_window("one")
    manager.test_window("two")
    assert len(manager.c.layout.info()["stacks"]) == 1
    manager.c.next_layout()
    assert len(manager.c.layout.info()["stacks"]) == 2
    manager.c.next_layout()
    manager.c.next_layout()
    manager.c.next_layout()
    assert len(manager.c.layout.info()["stacks"]) == 1


@manager_config
def test_setlayout(manager):
    assert not manager.c.layout.info()["name"] == "max"
    manager.c.group.setlayout("max")
    assert manager.c.layout.info()["name"] == "max"


@manager_config
def test_to_layout_index(manager):
    manager.c.to_layout_index(-1)
    assert manager.c.layout.info()["name"] == "max"
    manager.c.to_layout_index(-4)
    assert manager.c.layout.info()["name"] == "stack"
    with pytest.raises(SelectError):
        manager.c.to_layout.index(-5)
    manager.c.to_layout_index(-2)
    assert manager.c.layout.info()["name"] == "tile"


@manager_config
def test_adddelgroup(manager):
    manager.test_window("one")
    manager.c.addgroup("dummygroup")
    manager.c.addgroup("testgroup")
    assert "testgroup" in manager.c.get_groups().keys()

    manager.c.window.togroup("testgroup")
    manager.c.delgroup("testgroup")
    assert "testgroup" not in manager.c.get_groups().keys()
    # Assert that the test window is still a member of some group.
    assert sum(len(i["windows"]) for i in manager.c.get_groups().values())

    for i in list(manager.c.get_groups().keys())[:-1]:
        manager.c.delgroup(i)
    with pytest.raises(CommandException):
        manager.c.delgroup(list(manager.c.get_groups().keys())[0])

    # Assert that setting layout via addgroup works
    manager.c.addgroup("testgroup2", layout="max")
    assert manager.c.get_groups()["testgroup2"]["layout"] == "max"


@manager_config
def test_addgroupat(manager):
    manager.test_window("one")
    group_count = len(manager.c.get_groups())
    manager.c.addgroup("aa", index=1)

    assert len(manager.c.get_groups()) == group_count + 1
    assert list(manager.c.get_groups())[1] == "aa"


@manager_config
def test_delgroup(manager):
    manager.test_window("one")
    for i in ["a", "d", "c"]:
        manager.c.delgroup(i)
    with pytest.raises(CommandException):
        manager.c.delgroup("b")


@manager_config
def test_nextprevgroup(manager):
    manager.c.screen.next_group()
    assert manager.c.group.info()["name"] == "b"
    manager.c.screen.prev_group()
    assert manager.c.group.info()["name"] == "a"


def test_nextprevgroup_reload(manager_nospawn):
    manager_nospawn.start(lambda: BareConfig(file_path=configs_dir / "reloading.py"))
    # Current group will become unmanaged after reloading
    manager_nospawn.c.eval("self.old_group = self.current_group")
    manager_nospawn.c.reload_config()
    # Check that group has become unmanaged
    manager_nospawn.c.eval("self.new_group = self.current_group")
    assert "True" == manager_nospawn.c.eval("self.old_group != self.new_group")[1]
    # Unmanaged group should not change the group in the screen
    success, message = manager_nospawn.c.eval("self.old_group.screen.next_group()")
    assert "True" == manager_nospawn.c.eval("self.new_group == self.current_group")[1]
    assert success, message
    success, message = manager_nospawn.c.eval("self.old_group.screen.prev_group()")
    assert "True" == manager_nospawn.c.eval("self.new_group == self.current_group")[1]
    assert success, message


@manager_config
def test_toggle_group(manager):
    manager.c.group["a"].toscreen()
    manager.c.group["b"].toscreen()
    manager.c.screen.toggle_group("c")
    assert manager.c.group.info()["name"] == "c"
    manager.c.screen.toggle_group("c")
    assert manager.c.group.info()["name"] == "b"
    manager.c.screen.toggle_group()
    assert manager.c.group.info()["name"] == "c"


@manager_config
def test_static(manager):
    manager.test_window("one")
    manager.test_window("two")
    manager.c.window[manager.c.window.info()["id"]].static(
        screen=0,
        x=10,
        y=10,
        width=10,
        height=10,
    )
    info = manager.c.window.info()
    assert info["name"] == "one"
    manager.c.window.kill()
    assert_window_died(manager.c, info)
    with pytest.raises(CommandError):
        manager.c.window.info()
    info = manager.c.windows()[0]
    assert info["name"] == "two"
    assert (info["x"], info["y"], info["width"], info["height"]) == (10, 10, 10, 10)


@manager_config
def test_match(manager):
    manager.test_window("one")
    assert manager.c.window.info()["name"] == "one"
    assert not manager.c.window.info()["name"] == "nonexistent"


@manager_config
def test_default_float(manager):
    # change to 2 col stack
    manager.c.next_layout()
    assert len(manager.c.layout.info()["stacks"]) == 2
    manager.test_window("float")

    assert manager.c.group.info()["focus"] == "float"
    assert manager.c.window.info()["width"] == 100
    assert manager.c.window.info()["height"] == 100
    assert manager.c.window.info()["x"] == 350
    assert manager.c.window.info()["y"] == 240
    assert manager.c.window.info()["floating"] is True

    manager.c.window.move_floating(10, 20)
    assert manager.c.window.info()["width"] == 100
    assert manager.c.window.info()["height"] == 100
    assert manager.c.window.info()["x"] == 360
    assert manager.c.window.info()["y"] == 260
    assert manager.c.window.info()["floating"] is True

    manager.c.window.set_position_floating(10, 20)
    assert manager.c.window.info()["width"] == 100
    assert manager.c.window.info()["height"] == 100
    assert manager.c.window.info()["x"] == 10
    assert manager.c.window.info()["y"] == 20
    assert manager.c.window.info()["floating"] is True


@manager_config
def test_last_float_size(manager):
    """
    When you re-float something it would be preferable to have it use the previous float size
    """
    manager.test_window("one")
    assert manager.c.window.info()["name"] == "one"
    assert manager.c.window.info()["width"] == 798
    assert manager.c.window.info()["height"] == 578
    # float and it moves
    manager.c.window.toggle_floating()
    assert manager.c.window.info()["width"] == 100
    assert manager.c.window.info()["height"] == 100
    # resize
    manager.c.window.set_size_floating(50, 90)
    assert manager.c.window.info()["width"] == 50
    assert manager.c.window.info()["height"] == 90
    # back to not floating
    manager.c.window.toggle_floating()
    assert manager.c.window.info()["width"] == 798
    assert manager.c.window.info()["height"] == 578
    # float again, should use last float size
    manager.c.window.toggle_floating()
    assert manager.c.window.info()["width"] == 50
    assert manager.c.window.info()["height"] == 90

    # make sure it works through min and max
    manager.c.window.toggle_maximize()
    manager.c.window.toggle_minimize()
    manager.c.window.toggle_minimize()
    manager.c.window.toggle_floating()
    assert manager.c.window.info()["width"] == 50
    assert manager.c.window.info()["height"] == 90


@manager_config
def test_float_max_min_combo(manager):
    # change to 2 col stack
    manager.c.next_layout()
    assert len(manager.c.layout.info()["stacks"]) == 2
    manager.test_window("two")
    manager.test_window("one")

    assert manager.c.group.info()["focus"] == "one"
    assert manager.c.window.info()["width"] == 398
    assert manager.c.window.info()["height"] == 578
    assert manager.c.window.info()["x"] == 400
    assert manager.c.window.info()["y"] == 0
    assert manager.c.window.info()["floating"] is False

    manager.c.window.toggle_maximize()
    assert manager.c.window.info()["floating"] is True
    assert manager.c.window.info()["maximized"] is True
    assert manager.c.window.info()["width"] == 800
    assert manager.c.window.info()["height"] == 580
    assert manager.c.window.info()["x"] == 0
    assert manager.c.window.info()["y"] == 0

    manager.c.window.toggle_minimize()
    assert manager.c.group.info()["focus"] == "one"
    assert manager.c.window.info()["floating"] is True
    assert manager.c.window.info()["minimized"] is True
    assert manager.c.window.info()["width"] == 800
    assert manager.c.window.info()["height"] == 580
    assert manager.c.window.info()["x"] == 0
    assert manager.c.window.info()["y"] == 0

    manager.c.window.toggle_floating()
    assert manager.c.group.info()["focus"] == "one"
    assert manager.c.window.info()["floating"] is False
    assert manager.c.window.info()["minimized"] is False
    assert manager.c.window.info()["maximized"] is False
    assert manager.c.window.info()["width"] == 398
    assert manager.c.window.info()["height"] == 578
    assert manager.c.window.info()["x"] == 400
    assert manager.c.window.info()["y"] == 0


@manager_config
def test_toggle_fullscreen(manager):
    # change to 2 col stack
    manager.c.next_layout()
    assert len(manager.c.layout.info()["stacks"]) == 2
    manager.test_window("two")
    manager.test_window("one")

    assert manager.c.group.info()["focus"] == "one"
    assert manager.c.window.info()["width"] == 398
    assert manager.c.window.info()["height"] == 578
    assert manager.c.window.info()["float_info"] == {
        "y": 0,
        "x": 400,
        "width": 100,
        "height": 100,
    }
    assert manager.c.window.info()["x"] == 400
    assert manager.c.window.info()["y"] == 0

    manager.c.window.toggle_fullscreen()
    assert manager.c.window.info()["floating"] is True
    assert manager.c.window.info()["maximized"] is False
    assert manager.c.window.info()["fullscreen"] is True
    assert manager.c.window.info()["width"] == 800
    assert manager.c.window.info()["height"] == 600
    assert manager.c.window.info()["x"] == 0
    assert manager.c.window.info()["y"] == 0

    manager.c.window.toggle_fullscreen()
    assert manager.c.window.info()["floating"] is False
    assert manager.c.window.info()["maximized"] is False
    assert manager.c.window.info()["fullscreen"] is False
    assert manager.c.window.info()["width"] == 398
    assert manager.c.window.info()["height"] == 578
    assert manager.c.window.info()["x"] == 400
    assert manager.c.window.info()["y"] == 0


@manager_config
def test_toggle_max(manager):
    # change to 2 col stack
    manager.c.next_layout()
    assert len(manager.c.layout.info()["stacks"]) == 2
    manager.test_window("two")
    manager.test_window("one")

    assert manager.c.group.info()["focus"] == "one"
    assert manager.c.window.info()["width"] == 398
    assert manager.c.window.info()["height"] == 578
    assert manager.c.window.info()["float_info"] == {
        "y": 0,
        "x": 400,
        "width": 100,
        "height": 100,
    }
    assert manager.c.window.info()["x"] == 400
    assert manager.c.window.info()["y"] == 0

    manager.c.window.toggle_maximize()
    assert manager.c.window.info()["floating"] is True
    assert manager.c.window.info()["maximized"] is True
    assert manager.c.window.info()["width"] == 800
    assert manager.c.window.info()["height"] == 580
    assert manager.c.window.info()["x"] == 0
    assert manager.c.window.info()["y"] == 0

    manager.c.window.toggle_maximize()
    assert manager.c.window.info()["floating"] is False
    assert manager.c.window.info()["maximized"] is False
    assert manager.c.window.info()["width"] == 398
    assert manager.c.window.info()["height"] == 578
    assert manager.c.window.info()["x"] == 400
    assert manager.c.window.info()["y"] == 0


@manager_config
def test_toggle_min(manager):
    # change to 2 col stack
    manager.c.next_layout()
    assert len(manager.c.layout.info()["stacks"]) == 2
    manager.test_window("two")
    manager.test_window("one")

    assert manager.c.group.info()["focus"] == "one"
    assert manager.c.window.info()["width"] == 398
    assert manager.c.window.info()["height"] == 578
    assert manager.c.window.info()["float_info"] == {
        "y": 0,
        "x": 400,
        "width": 100,
        "height": 100,
    }
    assert manager.c.window.info()["x"] == 400
    assert manager.c.window.info()["y"] == 0

    manager.c.window.toggle_minimize()
    assert manager.c.group.info()["focus"] == "one"
    assert manager.c.window.info()["floating"] is True
    assert manager.c.window.info()["minimized"] is True
    assert manager.c.window.info()["width"] == 398
    assert manager.c.window.info()["height"] == 578
    assert manager.c.window.info()["x"] == 400
    assert manager.c.window.info()["y"] == 0

    manager.c.window.toggle_minimize()
    assert manager.c.group.info()["focus"] == "one"
    assert manager.c.window.info()["floating"] is False
    assert manager.c.window.info()["minimized"] is False
    assert manager.c.window.info()["width"] == 398
    assert manager.c.window.info()["height"] == 578
    assert manager.c.window.info()["x"] == 400
    assert manager.c.window.info()["y"] == 0


@manager_config
def test_toggle_floating(manager):
    manager.test_window("one")
    assert manager.c.window.info()["floating"] is False
    manager.c.window.toggle_floating()
    assert manager.c.window.info()["floating"] is True
    manager.c.window.toggle_floating()
    assert manager.c.window.info()["floating"] is False
    manager.c.window.toggle_floating()
    assert manager.c.window.info()["floating"] is True

    # change layout (should still be floating)
    manager.c.next_layout()
    assert manager.c.window.info()["floating"] is True


@manager_config
def test_floating_focus(manager):
    # change to 2 col stack
    manager.c.next_layout()
    assert len(manager.c.layout.info()["stacks"]) == 2
    manager.test_window("two")
    manager.test_window("one")
    assert manager.c.window.info()["width"] == 398
    assert manager.c.window.info()["height"] == 578
    manager.c.window.toggle_floating()
    manager.c.window.move_floating(10, 20)
    assert manager.c.window.info()["name"] == "one"
    assert manager.c.group.info()["focus"] == "one"
    # check what stack thinks is focus
    assert [x["current"] for x in manager.c.layout.info()["stacks"]] == [0, 0]

    # change focus to "one"
    manager.c.group.next_window()
    assert manager.c.window.info()["width"] == 398
    assert manager.c.window.info()["height"] == 578
    assert manager.c.window.info()["name"] != "one"
    assert manager.c.group.info()["focus"] != "one"
    # check what stack thinks is focus
    # check what stack thinks is focus
    assert [x["current"] for x in manager.c.layout.info()["stacks"]] == [0, 0]

    # focus back to one
    manager.c.group.next_window()
    assert manager.c.window.info()["name"] == "one"
    # check what stack thinks is focus
    assert [x["current"] for x in manager.c.layout.info()["stacks"]] == [0, 0]

    # now focusing via layout is borked (won't go to float)
    manager.c.layout.up()
    assert manager.c.window.info()["name"] != "one"
    manager.c.layout.up()
    assert manager.c.window.info()["name"] != "one"
    # check what stack thinks is focus
    assert [x["current"] for x in manager.c.layout.info()["stacks"]] == [0, 0]

    # focus back to one
    manager.c.group.next_window()
    assert manager.c.window.info()["name"] == "one"
    # check what stack thinks is focus
    assert [x["current"] for x in manager.c.layout.info()["stacks"]] == [0, 0]


@manager_config
def test_move_floating(manager):
    manager.test_window("one")
    # manager.test_window("one")
    assert manager.c.window.info()["width"] == 798
    assert manager.c.window.info()["height"] == 578

    assert manager.c.window.info()["x"] == 0
    assert manager.c.window.info()["y"] == 0
    manager.c.window.toggle_floating()
    assert manager.c.window.info()["floating"] is True

    manager.c.window.move_floating(10, 20)
    assert manager.c.window.info()["width"] == 100
    assert manager.c.window.info()["height"] == 100
    assert manager.c.window.info()["x"] == 10
    assert manager.c.window.info()["y"] == 20

    manager.c.window.set_size_floating(50, 90)
    assert manager.c.window.info()["width"] == 50
    assert manager.c.window.info()["height"] == 90
    assert manager.c.window.info()["x"] == 10
    assert manager.c.window.info()["y"] == 20

    manager.c.window.resize_floating(10, 20)
    assert manager.c.window.info()["width"] == 60
    assert manager.c.window.info()["height"] == 110
    assert manager.c.window.info()["x"] == 10
    assert manager.c.window.info()["y"] == 20

    manager.c.window.set_size_floating(10, 20)
    assert manager.c.window.info()["width"] == 10
    assert manager.c.window.info()["height"] == 20
    assert manager.c.window.info()["x"] == 10
    assert manager.c.window.info()["y"] == 20

    # change layout (x, y should be same)
    manager.c.next_layout()
    assert manager.c.window.info()["width"] == 10
    assert manager.c.window.info()["height"] == 20
    assert manager.c.window.info()["x"] == 10
    assert manager.c.window.info()["y"] == 20


@manager_config
def test_one_screen(manager):
    assert len(manager.c.get_screens()) == 1


@dualmonitor
@manager_config
def test_two_screens(manager):
    assert len(manager.c.get_screens()) == 2


@manager_config
def test_focus_stays_on_layout_switch(manager):
    manager.test_window("one")
    manager.test_window("two")

    # switch to a double stack layout
    manager.c.next_layout()

    # focus on a different window than the default
    manager.c.layout.next()

    # toggle the layout
    manager.c.next_layout()
    manager.c.prev_layout()

    assert manager.c.window.info()["name"] == "one"


@pytest.mark.parametrize("manager", [BareConfig, ManagerConfig], indirect=True)
def test_map_request(manager):
    manager.test_window("one")
    info = manager.c.get_groups()["a"]
    assert "one" in info["windows"]
    assert info["focus"] == "one"

    manager.test_window("two")
    info = manager.c.get_groups()["a"]
    assert "two" in info["windows"]
    assert info["focus"] == "two"


@pytest.mark.parametrize("manager", [BareConfig, ManagerConfig], indirect=True)
def test_unmap(manager):
    one = manager.test_window("one")
    two = manager.test_window("two")
    three = manager.test_window("three")
    info = manager.c.get_groups()["a"]
    assert info["focus"] == "three"

    assert len(manager.c.windows()) == 3
    manager.kill_window(three)

    assert len(manager.c.windows()) == 2
    info = manager.c.get_groups()["a"]
    assert info["focus"] == "two"

    manager.kill_window(two)
    assert len(manager.c.windows()) == 1
    info = manager.c.get_groups()["a"]
    assert info["focus"] == "one"

    manager.kill_window(one)
    assert len(manager.c.windows()) == 0
    info = manager.c.get_groups()["a"]
    assert info["focus"] is None


@pytest.mark.parametrize("manager", [BareConfig, ManagerConfig], indirect=True)
@multimonitor
def test_setgroup(manager):
    manager.test_window("one")
    manager.c.group["b"].toscreen()
    manager.groupconsistency()
    if len(manager.c.get_screens()) == 1:
        assert manager.c.get_groups()["a"]["screen"] is None
    else:
        assert manager.c.get_groups()["a"]["screen"] == 1
    assert manager.c.get_groups()["b"]["screen"] == 0

    manager.c.group["c"].toscreen()
    manager.groupconsistency()
    assert manager.c.get_groups()["c"]["screen"] == 0

    # Setting the current group once again switches back to the previous group
    manager.c.group["c"].toscreen(toggle=True)
    manager.groupconsistency()
    assert manager.c.group.info()["name"] == "b"


@pytest.mark.parametrize("manager", [BareConfig, ManagerConfig], indirect=True)
@multimonitor
def test_unmap_noscreen(manager):
    manager.test_window("one")
    pid = manager.test_window("two")
    assert len(manager.c.windows()) == 2
    manager.c.group["c"].toscreen()
    manager.groupconsistency()
    manager.c.status()
    assert len(manager.c.windows()) == 2
    manager.kill_window(pid)
    assert len(manager.c.windows()) == 1
    assert manager.c.get_groups()["a"]["focus"] == "one"


class TScreen(libqtile.config.Screen):
    group = _Group("")

    def set_group(self, x, save_prev=True):
        pass


def test_dx():
    s = TScreen(left=libqtile.bar.Gap(10))
    s._configure(None, 0, 0, 0, 100, 100, None)
    assert s.dx == 10


def test_dwidth():
    s = TScreen(left=libqtile.bar.Gap(10))
    s._configure(None, 0, 0, 0, 100, 100, None)
    assert s.dwidth == 90
    s.right = libqtile.bar.Gap(10)
    assert s.dwidth == 80


def test_dy():
    s = TScreen(top=libqtile.bar.Gap(10))
    s._configure(None, 0, 0, 0, 100, 100, None)
    assert s.dy == 10


def test_dheight():
    s = TScreen(top=libqtile.bar.Gap(10))
    s._configure(None, 0, 0, 0, 100, 100, None)
    assert s.dheight == 90
    s.bottom = libqtile.bar.Gap(10)
    assert s.dheight == 80


@manager_config
def test_labelgroup(manager):
    manager.c.group["a"].toscreen()
    assert manager.c.group["a"].info()["label"] == "a"

    manager.c.labelgroup()
    manager.c.widget["prompt"].fake_keypress("b")
    manager.c.widget["prompt"].fake_keypress("Return")
    assert manager.c.group["a"].info()["label"] == "b"

    manager.c.labelgroup()
    manager.c.widget["prompt"].fake_keypress("Return")
    assert manager.c.group["a"].info()["label"] == "a"


@manager_config
def test_change_loglevel(manager):
    assert manager.c.loglevel() == logging.INFO
    assert manager.c.loglevelname() == "INFO"
    manager.c.debug()
    assert manager.c.loglevel() == logging.DEBUG
    assert manager.c.loglevelname() == "DEBUG"
    manager.c.info()
    assert manager.c.loglevel() == logging.INFO
    assert manager.c.loglevelname() == "INFO"
    manager.c.warning()
    assert manager.c.loglevel() == logging.WARNING
    assert manager.c.loglevelname() == "WARNING"
    manager.c.error()
    assert manager.c.loglevel() == logging.ERROR
    assert manager.c.loglevelname() == "ERROR"
    manager.c.critical()
    assert manager.c.loglevel() == logging.CRITICAL
    assert manager.c.loglevelname() == "CRITICAL"


def test_switch_groups_cursor_warp(manager_nospawn):
    class SwitchGroupsCursorWarpConfig(ManagerConfig):
        cursor_warp = True
        layouts = [libqtile.layout.Stack(num_stacks=2), libqtile.layout.Max()]
        groups = [libqtile.config.Group("a"), libqtile.config.Group("b", layout="max")]

    manager_nospawn.start(SwitchGroupsCursorWarpConfig)

    manager_nospawn.test_window("one")
    manager_nospawn.test_window("two")
    manager_nospawn.c.layout.previous()

    assert_focused(manager_nospawn, "one")
    assert manager_nospawn.c.group.info()["name"] == "a"
    assert manager_nospawn.c.layout.info()["name"] == "stack"

    manager_nospawn.c.group["b"].toscreen()

    manager_nospawn.test_window("three")

    assert_focused(manager_nospawn, "three")
    assert manager_nospawn.c.group.info()["name"] == "b"
    assert manager_nospawn.c.layout.info()["name"] == "max"

    # do a fast switch to trigger races in focus behavior; unfortunately we
    # need the window in layout 'b' to map quite slowly (e.g. like firefox or
    # something), which it does not here most of the time.
    manager_nospawn.c.group["a"].toscreen()
    manager_nospawn.c.group["b"].toscreen()
    manager_nospawn.c.group["a"].toscreen()

    # make sure the right things are still focused
    assert_focused(manager_nospawn, "one")
    assert manager_nospawn.c.group.info()["name"] == "a"
    assert manager_nospawn.c.layout.info()["name"] == "stack"

    manager_nospawn.c.group["b"].toscreen()
    assert_focused(manager_nospawn, "three")
    assert manager_nospawn.c.group.info()["name"] == "b"
    assert manager_nospawn.c.layout.info()["name"] == "max"


def test_reload_config(manager_nospawn):
    # The test config uses presence of Qtile.test_data to change config values
    # Here we just want to check configurables are being updated within the live Qtile
    manager_nospawn.start(lambda: BareConfig(file_path=configs_dir / "reloading.py"))

    @Retry(ignore_exceptions=(AssertionError,))
    def assert_dd_appeared():
        assert "dd" in manager_nospawn.c.group.info()["windows"]

    # Original config
    assert manager_nospawn.c.eval("len(self.keys_map)") == (True, "1")
    assert manager_nospawn.c.eval("len(self._mouse_map)") == (True, "1")
    assert "".join(manager_nospawn.c.get_groups().keys()) == "12345S"
    assert len(manager_nospawn.c.group.info()["layouts"]) == 1
    assert manager_nospawn.c.widget["clock"].eval("self.background") == (True, "None")
    screens = manager_nospawn.c.get_screens()[0]
    assert screens["gaps"]["bottom"][3] == 24 and not screens["gaps"]["top"]
    assert len(manager_nospawn.c.internal_windows()) == 1
    assert manager_nospawn.c.eval("self.dgroups.key_binder") == (True, "None")
    assert manager_nospawn.c.eval("len(self.dgroups.rules)") == (True, "6")
    manager_nospawn.test_window("one")
    assert manager_nospawn.c.window.info()["floating"] is True
    manager_nospawn.c.window.kill()
    if manager_nospawn.backend.name == "x11":
        assert manager_nospawn.c.eval("self.core.wmname") == (True, "LG3D")
    manager_nospawn.c.group["S"].dropdown_toggle("dropdown1")  # Spawn dropdown
    assert_dd_appeared()
    manager_nospawn.c.group["S"].dropdown_toggle("dropdown1")  # Send it to ScratchPad

    # Reload #1 - with libqtile.qtile.test_data
    manager_nospawn.c.eval("self.test_data = 1")
    manager_nospawn.c.eval("self.test_data_config_evaluations = 0")
    manager_nospawn.c.reload_config()
    # should be readed twice (check+read), but no more
    assert manager_nospawn.c.eval("self.test_data_config_evaluations") == (True, "2")
    assert manager_nospawn.c.eval("len(self.keys_map)") == (True, "2")
    assert manager_nospawn.c.eval("len(self._mouse_map)") == (True, "2")
    assert "".join(manager_nospawn.c.get_groups().keys()) == "123456789S"
    assert len(manager_nospawn.c.group.info()["layouts"]) == 2
    assert manager_nospawn.c.widget["currentlayout"].eval("self.background") == (True, "#ff0000")
    screens = manager_nospawn.c.get_screens()[0]
    assert screens["gaps"]["top"][3] == 32 and not screens["gaps"]["bottom"]
    assert len(manager_nospawn.c.internal_windows()) == 1
    _, binder = manager_nospawn.c.eval("self.dgroups.key_binder")
    assert "function simple_key_binder" in binder
    assert manager_nospawn.c.eval("len(self.dgroups.rules)") == (True, "11")
    manager_nospawn.test_window("one")
    assert manager_nospawn.c.window.info()["floating"] is False
    manager_nospawn.c.window.kill()
    if manager_nospawn.backend.name == "x11":
        assert manager_nospawn.c.eval("self.core.wmname") == (True, "TEST")
    manager_nospawn.c.group["S"].dropdown_toggle("dropdown2")  # Spawn second dropdown
    assert_dd_appeared()
    manager_nospawn.c.group["S"].dropdown_toggle("dropdown1")  # Send it to ScratchPad
    assert "dd" in manager_nospawn.c.get_groups()["S"]["windows"]
    assert "dd" in manager_nospawn.c.get_groups()["S"]["windows"]

    # Reload #2 - back to without libqtile.qtile.test_data
    manager_nospawn.c.eval("del self.test_data")
    manager_nospawn.c.eval("del self.test_data_config_evaluations")
    manager_nospawn.c.reload_config()
    assert manager_nospawn.c.eval("len(self.keys_map)") == (True, "1")
    assert manager_nospawn.c.eval("len(self._mouse_map)") == (True, "1")
    # The last four groups persist within QtileState
    assert "".join(manager_nospawn.c.get_groups().keys()) == "12345S"
    assert len(manager_nospawn.c.group.info()["layouts"]) == 1
    assert manager_nospawn.c.widget["clock"].eval("self.background") == (True, "None")
    screens = manager_nospawn.c.get_screens()[0]
    assert screens["gaps"]["bottom"][3] == 24 and not screens["gaps"]["top"]
    assert len(manager_nospawn.c.internal_windows()) == 1
    assert manager_nospawn.c.eval("self.dgroups.key_binder") == (True, "None")
    assert manager_nospawn.c.eval("len(self.dgroups.rules)") == (True, "6")
    manager_nospawn.test_window("one")
    assert manager_nospawn.c.window.info()["floating"] is True
    manager_nospawn.c.window.kill()
    if manager_nospawn.backend.name == "x11":
        assert manager_nospawn.c.eval("self.core.wmname") == (True, "LG3D")
    assert "dd" in manager_nospawn.c.get_groups()["S"]["windows"]  # First dropdown persists
    assert "dd" in manager_nospawn.c.get_groups()["1"]["windows"]  # Second orphans to group


class CommandsConfig(Config):
    screens = [
        libqtile.config.Screen(
            bottom=libqtile.bar.Bar([libqtile.widget.Systray()], 20),
        )
    ]


@pytest.mark.parametrize("manager", [CommandsConfig], indirect=True)
def test_windows_from_commands(manager):
    manager.test_window("one")
    assert len(manager.c.items("window")) == 2  # This command returns windows including bars
    windows = manager.c.windows()  # Whereas this one is just regular windows
    assert len(windows) == 1
    # And the Systray is absent
    assert "TestWindow" in windows[0]["wm_class"]


class DuplicateWidgetsConfig(ManagerConfig):
    screens = [
        libqtile.config.Screen(
            bottom=libqtile.bar.Bar(
                [
                    libqtile.widget.Prompt(),
                    libqtile.widget.Prompt(),
                    libqtile.widget.Prompt(),
                    libqtile.widget.Prompt(name="foo"),
                    libqtile.widget.GroupBox(),
                    libqtile.widget.GroupBox(),
                    libqtile.widget.GroupBox(),
                    libqtile.widget.GroupBox(name="foo"),
                ],
                20,
            ),
        )
    ]


duplicate_widgets_config = pytest.mark.parametrize(
    "manager", [DuplicateWidgetsConfig], indirect=True
)


@duplicate_widgets_config
def test_widget_duplicate_names(manager):
    # Verify every widget is in widgets_map
    _, result = manager.c.eval("len(self.widgets_map)")
    assert int(result) == len(DuplicateWidgetsConfig.screens[0].bottom.widgets)

    # Verify renaming in qtile.widgets_map
    assert manager.c.widget["prompt"]
    assert manager.c.widget["prompt_1"]
    assert manager.c.widget["prompt_2"]
    assert manager.c.widget["groupbox"]
    assert manager.c.widget["groupbox_1"]
    assert manager.c.widget["groupbox_2"]
    assert manager.c.widget["foo"]
    assert manager.c.widget["foo_1"]

    # No renaming of actual widgets
    assert manager.c.bar["bottom"].info()["widgets"][0]["name"] == "prompt"
    assert manager.c.bar["bottom"].info()["widgets"][1]["name"] == "prompt"
    assert manager.c.bar["bottom"].info()["widgets"][2]["name"] == "prompt"
    assert manager.c.bar["bottom"].info()["widgets"][3]["name"] == "foo"
    assert manager.c.bar["bottom"].info()["widgets"][4]["name"] == "groupbox"
    assert manager.c.bar["bottom"].info()["widgets"][5]["name"] == "groupbox"
    assert manager.c.bar["bottom"].info()["widgets"][6]["name"] == "groupbox"
    assert manager.c.bar["bottom"].info()["widgets"][7]["name"] == "foo"


@duplicate_widgets_config
def test_widget_duplicate_warnings(manager):
    records = manager.get_log_buffer().splitlines()

    # We need to filter out other potential log messages here
    records = [r for r in records if "The following widgets" in r]

    assert len(records) == 1

    for w in ["prompt_1", "prompt_2", "groupbox_1", "groupbox_2", "foo_1"]:
        assert w in records[0]

    # Check this message level was info
    assert all([r.startswith("INFO") for r in records])
