# Copyright (c) 2011 Florian Mounier
# Copyright (c) 2011 Anshuman Bhaduri
# Copyright (c) 2012-2014 Tycho Andersen
# Copyright (c) 2013 xarvh
# Copyright (c) 2013 Craig Barnes
# Copyright (c) 2014 Sean Vig
# Copyright (c) 2014 Adi Sieker
# Copyright (c) 2014 Sebastien Blot
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

import pytest
import subprocess
import time

import libqtile
import libqtile.layout
import libqtile.bar
import libqtile.command
import libqtile.widget
import libqtile.manager
import libqtile.config
import libqtile.hook
import libqtile.confreader

from .conftest import whereis, BareConfig, no_xinerama, retry


class ManagerConfig(object):
    auto_fullscreen = True
    groups = [
        libqtile.config.Group("a"),
        libqtile.config.Group("b"),
        libqtile.config.Group("c"),
        libqtile.config.Group("d")
    ]
    layouts = [
        libqtile.layout.stack.Stack(num_stacks=1),
        libqtile.layout.stack.Stack(num_stacks=2),
        libqtile.layout.tile.Tile(ratio=0.5),
        libqtile.layout.max.Max()
    ]
    floating_layout = libqtile.layout.floating.Floating(
        float_rules=[dict(wmclass="xclock")])
    keys = [
        libqtile.config.Key(
            ["control"],
            "k",
            libqtile.command._Call([("layout", None)], "up")
        ),
        libqtile.config.Key(
            ["control"],
            "j",
            libqtile.command._Call([("layout", None)], "down")
        ),
    ]
    mouse = []
    screens = [libqtile.config.Screen(
        bottom=libqtile.bar.Bar(
            [
                libqtile.widget.GroupBox(),
            ],
            20
        ),
    )]
    main = None
    follow_mouse_focus = True
    focus_on_mapped_windows = True


manager_config = pytest.mark.parametrize("qtile", [ManagerConfig], indirect=True)


@manager_config
def test_screen_dim(qtile):
    # self.c.restart()

    qtile.testXclock()
    assert qtile.c.screen.info()["index"] == 0
    assert qtile.c.screen.info()["x"] == 0
    assert qtile.c.screen.info()["width"] == 800
    assert qtile.c.group.info()["name"] == 'a'
    assert qtile.c.group.info()["focus"] == 'xclock'

    qtile.c.to_screen(1)
    qtile.testXeyes()
    assert qtile.c.screen.info()["index"] == 1
    assert qtile.c.screen.info()["x"] == 800
    assert qtile.c.screen.info()["width"] == 640
    assert qtile.c.group.info()["name"] == 'b'
    assert qtile.c.group.info()["focus"] == 'xeyes'

    qtile.c.to_screen(0)
    assert qtile.c.screen.info()["index"] == 0
    assert qtile.c.screen.info()["x"] == 0
    assert qtile.c.screen.info()["width"] == 800
    assert qtile.c.group.info()["name"] == 'a'
    assert qtile.c.group.info()["focus"] == 'xclock'


@pytest.mark.parametrize("xephyr", [{"xoffset": 0}], indirect=True)
@manager_config
def test_clone_dim(qtile):
    self = qtile

    self.testXclock()
    assert self.c.screen.info()["index"] == 0
    assert self.c.screen.info()["x"] == 0
    assert self.c.screen.info()["width"] == 800
    assert self.c.group.info()["name"] == 'a'
    assert self.c.group.info()["focus"] == 'xclock'

    assert len(self.c.screens()) == 1


@manager_config
def test_to_screen(qtile):
    self = qtile

    assert self.c.screen.info()["index"] == 0
    self.c.to_screen(1)
    assert self.c.screen.info()["index"] == 1
    self.testWindow("one")
    self.c.to_screen(0)
    self.testWindow("two")

    ga = self.c.groups()["a"]
    assert ga["windows"] == ["two"]

    gb = self.c.groups()["b"]
    assert gb["windows"] == ["one"]

    assert self.c.window.info()["name"] == "two"
    self.c.next_screen()
    assert self.c.window.info()["name"] == "one"
    self.c.next_screen()
    assert self.c.window.info()["name"] == "two"
    self.c.prev_screen()
    assert self.c.window.info()["name"] == "one"


@manager_config
def test_togroup(qtile):
    self = qtile

    self.testWindow("one")
    with pytest.raises(libqtile.command.CommandError):
        self.c.window.togroup("nonexistent")
    assert self.c.groups()["a"]["focus"] == "one"
    self.c.window.togroup("a")
    assert self.c.groups()["a"]["focus"] == "one"
    self.c.window.togroup("b")
    assert self.c.groups()["b"]["focus"] == "one"
    assert self.c.groups()["a"]["focus"] is None
    self.c.to_screen(1)
    self.c.window.togroup("c")
    assert self.c.groups()["c"]["focus"] == "one"


@manager_config
def test_resize(qtile):
    self = qtile
    self.c.screen[0].resize(x=10, y=10, w=100, h=100)
    @retry(ignore_exceptions=(AssertionError), fail_msg="Screen didn't resize")
    def run():
        d = self.c.screen[0].info()
        assert d['width'] == 100
        assert d['height'] == 100
        return d
    d = run()
    assert d['x'] == d['y'] == 10


@no_xinerama
def test_minimal(qtile):
    assert qtile.c.status() == "OK"


@manager_config
@no_xinerama
def test_events(qtile):
    assert qtile.c.status() == "OK"


# FIXME: failing test disabled. For some reason we don't seem
# to have a keymap in Xnest or Xephyr 99% of the time.
@manager_config
@no_xinerama
def test_keypress(qtile):
    self = qtile

    self.testWindow("one")
    self.testWindow("two")
    v = self.c.simulate_keypress(["unknown"], "j")
    assert v.startswith("Unknown modifier")
    assert self.c.groups()["a"]["focus"] == "two"
    self.c.simulate_keypress(["control"], "j")
    assert self.c.groups()["a"]["focus"] == "one"


@manager_config
@no_xinerama
def test_spawn(qtile):
    # Spawn something with a pid greater than init's
    assert int(qtile.c.spawn("true")) > 1


@manager_config
@no_xinerama
def test_spawn_list(qtile):
    # Spawn something with a pid greater than init's
    assert int(qtile.c.spawn(["echo", "true"])) > 1

@retry(ignore_exceptions=(AssertionError,), fail_msg='Window did not die!')
def assert_window_died(client, window_info):
    client.sync()
    wid = window_info['id']
    assert wid not in set([x['id'] for x in client.windows()])

@manager_config
@no_xinerama
def test_kill_window(qtile):
    qtile.testWindow("one")
    qtile.testwindows = []
    window_info = qtile.c.window.info()
    qtile.c.window[window_info["id"]].kill()
    assert_window_died(qtile.c, window_info)

@manager_config
@no_xinerama
def test_kill_other(qtile):
    self = qtile

    self.c.group.setlayout("tile")
    one = self.testWindow("one")
    assert self.c.window.info()["width"] == 798
    window_one_info = self.c.window.info()
    assert self.c.window.info()["height"] == 578
    two = self.testWindow("two")
    assert self.c.window.info()["name"] == "two"
    assert self.c.window.info()["width"] == 398
    assert self.c.window.info()["height"] == 578
    assert len(self.c.windows()) == 2

    self.kill_window(one)
    assert_window_died(self.c, window_one_info)

    assert self.c.window.info()["name"] == "two"
    assert self.c.window.info()["width"] == 798
    assert self.c.window.info()["height"] == 578


@manager_config
@no_xinerama
def test_regression_groupswitch(qtile):
    self = qtile

    self.c.group["c"].toscreen()
    self.c.group["d"].toscreen()
    assert self.c.groups()["c"]["screen"] is None


@manager_config
@no_xinerama
def test_next_layout(qtile):
    self = qtile

    self.testWindow("one")
    self.testWindow("two")
    assert len(self.c.layout.info()["stacks"]) == 1
    self.c.next_layout()
    assert len(self.c.layout.info()["stacks"]) == 2
    self.c.next_layout()
    self.c.next_layout()
    self.c.next_layout()
    assert len(self.c.layout.info()["stacks"]) == 1


@manager_config
@no_xinerama
def test_setlayout(qtile):
    self = qtile

    assert not self.c.layout.info()["name"] == "max"
    self.c.group.setlayout("max")
    assert self.c.layout.info()["name"] == "max"


@manager_config
@no_xinerama
def test_adddelgroup(qtile):
    self = qtile

    self.testWindow("one")
    self.c.addgroup("dummygroup")
    self.c.addgroup("testgroup")
    assert "testgroup" in self.c.groups().keys()
    self.c.window.togroup("testgroup")
    self.c.delgroup("testgroup")
    assert "testgroup" not in self.c.groups().keys()
    # Assert that the test window is still a member of some group.
    assert sum(len(i["windows"]) for i in self.c.groups().values())

    for i in list(self.c.groups().keys())[:-1]:
        self.c.delgroup(i)
    with pytest.raises(libqtile.command.CommandException):
        self.c.delgroup(list(self.c.groups().keys())[0])


@manager_config
@no_xinerama
def test_delgroup(qtile):
    self = qtile

    self.testWindow("one")
    for i in ['a', 'd', 'c']:
        self.c.delgroup(i)
    with pytest.raises(libqtile.command.CommandException):
        self.c.delgroup('b')


@manager_config
@no_xinerama
def test_nextprevgroup(qtile):
    self = qtile

    start = self.c.group.info()["name"]
    ret = self.c.screen.next_group()
    assert self.c.group.info()["name"] != start
    assert self.c.group.info()["name"] == ret
    ret = self.c.screen.prev_group()
    assert self.c.group.info()["name"] == start


@manager_config
@no_xinerama
def test_toggle_group(qtile):
    self = qtile

    self.c.group["a"].toscreen()
    self.c.group["b"].toscreen()
    self.c.screen.toggle_group("c")
    assert self.c.group.info()["name"] == "c"
    self.c.screen.toggle_group("c")
    assert self.c.group.info()["name"] == "b"
    self.c.screen.toggle_group()
    assert self.c.group.info()["name"] == "c"


@manager_config
@no_xinerama
def test_inspect_xeyes(qtile):
    self = qtile

    self.testXeyes()
    assert self.c.window.inspect()


@manager_config
@no_xinerama
def test_inspect_xterm(qtile):
    self = qtile

    self.testXterm()
    assert self.c.window.inspect()["wm_class"]


@manager_config
@no_xinerama
def test_static(qtile):
    self = qtile

    self.testXeyes()
    self.testWindow("one")
    self.c.window[self.c.window.info()["id"]].static(0, 0, 0, 100, 100)


@manager_config
@no_xinerama
def test_match(qtile):
    self = qtile

    self.testXeyes()
    assert self.c.window.match(wname="xeyes")
    assert not self.c.window.match(wname="nonexistent")


@manager_config
@no_xinerama
def test_default_float(qtile):
    self = qtile

    # change to 2 col stack
    self.c.next_layout()
    assert len(self.c.layout.info()["stacks"]) == 2
    self.testXclock()

    assert self.c.group.info()['focus'] == 'xclock'
    assert self.c.window.info()['width'] == 164
    assert self.c.window.info()['height'] == 164
    assert self.c.window.info()['x'] == 0
    assert self.c.window.info()['y'] == 0
    assert self.c.window.info()['floating'] is True

    self.c.window.move_floating(10, 20, 42, 42)
    assert self.c.window.info()['width'] == 164
    assert self.c.window.info()['height'] == 164
    assert self.c.window.info()['x'] == 10
    assert self.c.window.info()['y'] == 20
    assert self.c.window.info()['floating'] is True


@manager_config
@no_xinerama
def test_last_float_size(qtile):
    """
    When you re-float something it would be preferable to have it use the previous float size
    """
    self = qtile

    self.testXeyes()
    assert self.c.window.info()['name'] == 'xeyes'
    assert self.c.window.info()['width'] == 798
    assert self.c.window.info()['height'] == 578
    # float and it moves
    self.c.window.toggle_floating()
    assert self.c.window.info()['width'] == 150
    assert self.c.window.info()['height'] == 100
    # resize
    self.c.window.set_size_floating(50, 90, 42, 42)
    assert self.c.window.info()['width'] == 50
    assert self.c.window.info()['height'] == 90
    # back to not floating
    self.c.window.toggle_floating()
    assert self.c.window.info()['width'] == 798
    assert self.c.window.info()['height'] == 578
    # float again, should use last float size
    self.c.window.toggle_floating()
    assert self.c.window.info()['width'] == 50
    assert self.c.window.info()['height'] == 90

    # make sure it works through min and max
    self.c.window.toggle_maximize()
    self.c.window.toggle_minimize()
    self.c.window.toggle_minimize()
    self.c.window.toggle_floating()
    assert self.c.window.info()['width'] == 50
    assert self.c.window.info()['height'] == 90


@manager_config
@no_xinerama
def test_float_max_min_combo(qtile):
    self = qtile

    # change to 2 col stack
    self.c.next_layout()
    assert len(self.c.layout.info()["stacks"]) == 2
    self.testXterm()
    self.testXeyes()

    assert self.c.group.info()['focus'] == 'xeyes'
    assert self.c.window.info()['width'] == 398
    assert self.c.window.info()['height'] == 578
    assert self.c.window.info()['x'] == 400
    assert self.c.window.info()['y'] == 0
    assert self.c.window.info()['floating'] is False

    self.c.window.toggle_maximize()
    assert self.c.window.info()['floating'] is True
    assert self.c.window.info()['maximized'] is True
    assert self.c.window.info()['width'] == 800
    assert self.c.window.info()['height'] == 580
    assert self.c.window.info()['x'] == 0
    assert self.c.window.info()['y'] == 0

    self.c.window.toggle_minimize()
    assert self.c.group.info()['focus'] == 'xeyes'
    assert self.c.window.info()['floating'] is True
    assert self.c.window.info()['minimized'] is True
    assert self.c.window.info()['width'] == 800
    assert self.c.window.info()['height'] == 580
    assert self.c.window.info()['x'] == 0
    assert self.c.window.info()['y'] == 0

    self.c.window.toggle_floating()
    assert self.c.group.info()['focus'] == 'xeyes'
    assert self.c.window.info()['floating'] is False
    assert self.c.window.info()['minimized'] is False
    assert self.c.window.info()['maximized'] is False
    assert self.c.window.info()['width'] == 398
    assert self.c.window.info()['height'] == 578
    assert self.c.window.info()['x'] == 400
    assert self.c.window.info()['y'] == 0


@manager_config
@no_xinerama
def test_toggle_fullscreen(qtile):
    self = qtile

    # change to 2 col stack
    self.c.next_layout()
    assert len(self.c.layout.info()["stacks"]) == 2
    self.testXterm()
    self.testXeyes()

    assert self.c.group.info()['focus'] == 'xeyes'
    assert self.c.window.info()['width'] == 398
    assert self.c.window.info()['height'] == 578
    assert self.c.window.info()['float_info'] == {
        'y': 0, 'x': 400, 'width': 150, 'height': 100}
    assert self.c.window.info()['x'] == 400
    assert self.c.window.info()['y'] == 0

    self.c.window.toggle_fullscreen()
    assert self.c.window.info()['floating'] is True
    assert self.c.window.info()['maximized'] is False
    assert self.c.window.info()['fullscreen'] is True
    assert self.c.window.info()['width'] == 800
    assert self.c.window.info()['height'] == 600
    assert self.c.window.info()['x'] == 0
    assert self.c.window.info()['y'] == 0

    self.c.window.toggle_fullscreen()
    assert self.c.window.info()['floating'] is False
    assert self.c.window.info()['maximized'] is False
    assert self.c.window.info()['fullscreen'] is False
    assert self.c.window.info()['width'] == 398
    assert self.c.window.info()['height'] == 578
    assert self.c.window.info()['x'] == 400
    assert self.c.window.info()['y'] == 0


@manager_config
@no_xinerama
def test_toggle_max(qtile):
    self = qtile

    # change to 2 col stack
    self.c.next_layout()
    assert len(self.c.layout.info()["stacks"]) == 2
    self.testXterm()
    self.testXeyes()

    assert self.c.group.info()['focus'] == 'xeyes'
    assert self.c.window.info()['width'] == 398
    assert self.c.window.info()['height'] == 578
    assert self.c.window.info()['float_info'] == {
        'y': 0, 'x': 400, 'width': 150, 'height': 100}
    assert self.c.window.info()['x'] == 400
    assert self.c.window.info()['y'] == 0

    self.c.window.toggle_maximize()
    assert self.c.window.info()['floating'] is True
    assert self.c.window.info()['maximized'] is True
    assert self.c.window.info()['width'] == 800
    assert self.c.window.info()['height'] == 580
    assert self.c.window.info()['x'] == 0
    assert self.c.window.info()['y'] == 0

    self.c.window.toggle_maximize()
    assert self.c.window.info()['floating'] is False
    assert self.c.window.info()['maximized'] is False
    assert self.c.window.info()['width'] == 398
    assert self.c.window.info()['height'] == 578
    assert self.c.window.info()['x'] == 400
    assert self.c.window.info()['y'] == 0


@manager_config
@no_xinerama
def test_toggle_min(qtile):
    self = qtile

    # change to 2 col stack
    self.c.next_layout()
    assert len(self.c.layout.info()["stacks"]) == 2
    self.testXterm()
    self.testXeyes()

    assert self.c.group.info()['focus'] == 'xeyes'
    assert self.c.window.info()['width'] == 398
    assert self.c.window.info()['height'] == 578
    assert self.c.window.info()['float_info'] == {
        'y': 0, 'x': 400, 'width': 150, 'height': 100}
    assert self.c.window.info()['x'] == 400
    assert self.c.window.info()['y'] == 0

    self.c.window.toggle_minimize()
    assert self.c.group.info()['focus'] == 'xeyes'
    assert self.c.window.info()['floating'] is True
    assert self.c.window.info()['minimized'] is True
    assert self.c.window.info()['width'] == 398
    assert self.c.window.info()['height'] == 578
    assert self.c.window.info()['x'] == 400
    assert self.c.window.info()['y'] == 0

    self.c.window.toggle_minimize()
    assert self.c.group.info()['focus'] == 'xeyes'
    assert self.c.window.info()['floating'] is False
    assert self.c.window.info()['minimized'] is False
    assert self.c.window.info()['width'] == 398
    assert self.c.window.info()['height'] == 578
    assert self.c.window.info()['x'] == 400
    assert self.c.window.info()['y'] == 0


@manager_config
@no_xinerama
def test_toggle_floating(qtile):
    self = qtile

    self.testXeyes()
    assert self.c.window.info()['floating'] is False
    self.c.window.toggle_floating()
    assert self.c.window.info()['floating'] is True
    self.c.window.toggle_floating()
    assert self.c.window.info()['floating'] is False
    self.c.window.toggle_floating()
    assert self.c.window.info()['floating'] is True

    # change layout (should still be floating)
    self.c.next_layout()
    assert self.c.window.info()['floating'] is True


@manager_config
@no_xinerama
def test_floating_focus(qtile):
    self = qtile

    # change to 2 col stack
    self.c.next_layout()
    assert len(self.c.layout.info()["stacks"]) == 2
    self.testXterm()
    self.testXeyes()
    # self.testWindow("one")
    assert self.c.window.info()['width'] == 398
    assert self.c.window.info()['height'] == 578
    self.c.window.toggle_floating()
    self.c.window.move_floating(10, 20, 42, 42)
    assert self.c.window.info()['name'] == 'xeyes'
    assert self.c.group.info()['focus'] == 'xeyes'
    # check what stack thinks is focus
    assert [x['current'] for x in self.c.layout.info()['stacks']] == [0, 0]

    # change focus to xterm
    self.c.group.next_window()
    assert self.c.window.info()['width'] == 398
    assert self.c.window.info()['height'] == 578
    assert self.c.window.info()['name'] != 'xeyes'
    assert self.c.group.info()['focus'] != 'xeyes'
    # check what stack thinks is focus
    # check what stack thinks is focus
    assert [x['current'] for x in self.c.layout.info()['stacks']] == [0, 0]

    # focus back to xeyes
    self.c.group.next_window()
    assert self.c.window.info()['name'] == 'xeyes'
    # check what stack thinks is focus
    assert [x['current'] for x in self.c.layout.info()['stacks']] == [0, 0]

    # now focusing via layout is borked (won't go to float)
    self.c.layout.up()
    assert self.c.window.info()['name'] != 'xeyes'
    self.c.layout.up()
    assert self.c.window.info()['name'] != 'xeyes'
    # check what stack thinks is focus
    assert [x['current'] for x in self.c.layout.info()['stacks']] == [0, 0]

    # focus back to xeyes
    self.c.group.next_window()
    assert self.c.window.info()['name'] == 'xeyes'
    # check what stack thinks is focus
    assert [x['current'] for x in self.c.layout.info()['stacks']] == [0, 0]


@manager_config
@no_xinerama
def test_move_floating(qtile):
    self = qtile

    self.testXeyes()
    # self.testWindow("one")
    assert self.c.window.info()['width'] == 798
    assert self.c.window.info()['height'] == 578

    assert self.c.window.info()['x'] == 0
    assert self.c.window.info()['y'] == 0
    self.c.window.toggle_floating()
    assert self.c.window.info()['floating'] is True

    self.c.window.move_floating(10, 20, 42, 42)
    assert self.c.window.info()['width'] == 150
    assert self.c.window.info()['height'] == 100
    assert self.c.window.info()['x'] == 10
    assert self.c.window.info()['y'] == 20

    self.c.window.set_size_floating(50, 90, 42, 42)
    assert self.c.window.info()['width'] == 50
    assert self.c.window.info()['height'] == 90
    assert self.c.window.info()['x'] == 10
    assert self.c.window.info()['y'] == 20

    self.c.window.resize_floating(10, 20, 42, 42)
    assert self.c.window.info()['width'] == 60
    assert self.c.window.info()['height'] == 110
    assert self.c.window.info()['x'] == 10
    assert self.c.window.info()['y'] == 20

    self.c.window.set_size_floating(10, 20, 42, 42)
    assert self.c.window.info()['width'] == 10
    assert self.c.window.info()['height'] == 20
    assert self.c.window.info()['x'] == 10
    assert self.c.window.info()['y'] == 20

    # change layout (x, y should be same)
    self.c.next_layout()
    assert self.c.window.info()['width'] == 10
    assert self.c.window.info()['height'] == 20
    assert self.c.window.info()['x'] == 10
    assert self.c.window.info()['y'] == 20


@manager_config
@no_xinerama
def test_screens(qtile):
    self = qtile

    assert len(self.c.screens())


@manager_config
@no_xinerama
def test_rotate(qtile):
    self = qtile

    self.testWindow("one")
    s = self.c.screens()[0]
    height, width = s["height"], s["width"]
    subprocess.call(
        [
            "xrandr",
            "--output", "default",
            "-display", self.display,
            "--rotate", "left"
        ],
        stderr=subprocess.PIPE,
        stdout=subprocess.PIPE
    )

    @retry(ignore_exceptions=(AssertionError,), fail_msg="Screen did not rotate")
    def run():
        s = self.c.screens()[0]
        assert s['width'] == height
        assert s['height'] == width
        return True
    run()


# TODO: see note on test_resize
@manager_config
@no_xinerama
def test_resize_(qtile):
    self = qtile

    self.testWindow("one")
    subprocess.call(
        [
            "xrandr",
            "-s", "480x640",
            "-display", self.display
        ]
    )
    @retry(ignore_exceptions=(AssertionError,), fail_msg="Screen did not resize")
    def run():
        d = self.c.screen.info()
        assert d['width'] == 480
        assert d['height'] == 640
        return True
    run()


@manager_config
@no_xinerama
def test_focus_stays_on_layout_switch(qtile):
    qtile.testWindow("one")
    qtile.testWindow("two")

    # switch to a double stack layout
    qtile.c.next_layout()

    # focus on a different window than the default
    qtile.c.layout.next()

    # toggle the layout
    qtile.c.next_layout()
    qtile.c.prev_layout()

    assert qtile.c.window.info()['name'] == 'one'


@pytest.mark.parametrize("qtile", [BareConfig, ManagerConfig], indirect=True)
@pytest.mark.parametrize("xephyr", [{"xinerama": True}, {"xinerama": False}], indirect=True)
def test_xeyes(qtile):
    qtile.testXeyes()


@pytest.mark.parametrize("qtile", [BareConfig, ManagerConfig], indirect=True)
@pytest.mark.parametrize("xephyr", [{"xinerama": True}, {"xinerama": False}], indirect=True)
def test_xterm(qtile):
    qtile.testXterm()


@pytest.mark.parametrize("qtile", [BareConfig, ManagerConfig], indirect=True)
@pytest.mark.parametrize("xephyr", [{"xinerama": True}, {"xinerama": False}], indirect=True)
def test_xterm_kill_window(qtile):
    self = qtile

    self.testXterm()
    window_info = self.c.window.info()
    self.c.window.kill()
    assert_window_died(self.c, window_info)


@pytest.mark.parametrize("qtile", [BareConfig, ManagerConfig], indirect=True)
@pytest.mark.parametrize("xephyr", [{"xinerama": True}, {"xinerama": False}], indirect=True)
def test_map_request(qtile):
    self = qtile

    self.testWindow("one")
    info = self.c.groups()["a"]
    assert "one" in info["windows"]
    assert info["focus"] == "one"

    self.testWindow("two")
    info = self.c.groups()["a"]
    assert "two" in info["windows"]
    assert info["focus"] == "two"


@pytest.mark.parametrize("qtile", [BareConfig, ManagerConfig], indirect=True)
@pytest.mark.parametrize("xephyr", [{"xinerama": True}, {"xinerama": False}], indirect=True)
def test_unmap(qtile):
    self = qtile

    one = self.testWindow("one")
    two = self.testWindow("two")
    three = self.testWindow("three")
    info = self.c.groups()["a"]
    assert info["focus"] == "three"

    assert len(self.c.windows()) == 3
    self.kill_window(three)

    assert len(self.c.windows()) == 2
    info = self.c.groups()["a"]
    assert info["focus"] == "two"

    self.kill_window(two)
    assert len(self.c.windows()) == 1
    info = self.c.groups()["a"]
    assert info["focus"] == "one"

    self.kill_window(one)
    assert len(self.c.windows()) == 0
    info = self.c.groups()["a"]
    assert info["focus"] is None


@pytest.mark.parametrize("qtile", [BareConfig, ManagerConfig], indirect=True)
@pytest.mark.parametrize("xephyr", [{"xinerama": True}, {"xinerama": False}], indirect=True)
def test_setgroup(qtile):
    self = qtile

    self.testWindow("one")
    self.c.group["b"].toscreen()
    self.groupconsistency()
    if len(self.c.screens()) == 1:
        assert self.c.groups()["a"]["screen"] is None
    else:
        assert self.c.groups()["a"]["screen"] == 1
    assert self.c.groups()["b"]["screen"] == 0
    self.c.group["c"].toscreen()
    self.groupconsistency()
    assert self.c.groups()["c"]["screen"] == 0


@pytest.mark.parametrize("qtile", [BareConfig, ManagerConfig], indirect=True)
@pytest.mark.parametrize("xephyr", [{"xinerama": True}, {"xinerama": False}], indirect=True)
def test_unmap_noscreen(qtile):
    self = qtile

    self.testWindow("one")
    pid = self.testWindow("two")
    assert len(self.c.windows()) == 2
    self.c.group["c"].toscreen()
    self.groupconsistency()
    self.c.status()
    assert len(self.c.windows()) == 2
    self.kill_window(pid)
    assert len(self.c.windows()) == 1
    assert self.c.groups()["a"]["focus"] == "one"


def test_init():
    with pytest.raises(libqtile.manager.QtileError):
        libqtile.config.Key([], "unknown", libqtile.command._Call("base", None, "foo"))
    with pytest.raises(libqtile.manager.QtileError):
        libqtile.config.Key(["unknown"], "x", libqtile.command._Call("base", None, "foo"))


class TScreen(libqtile.config.Screen):
    def setGroup(self, x, save_prev=True):
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


class _Config(object):
    groups = [
        libqtile.config.Group("a"),
        libqtile.config.Group("b"),
        libqtile.config.Group("c"),
        libqtile.config.Group("d")
    ]
    layouts = [
        libqtile.layout.stack.Stack(num_stacks=1),
        libqtile.layout.stack.Stack(num_stacks=2)
    ]
    floating_layout = libqtile.layout.floating.Floating()
    keys = [
        libqtile.config.Key(
            ["control"],
            "k",
            libqtile.command._Call([("layout", None)], "up")
        ),
        libqtile.config.Key(
            ["control"],
            "j",
            libqtile.command._Call([("layout", None)], "down")
        ),
    ]
    mouse = []
    screens = [libqtile.config.Screen(
        bottom=libqtile.bar.Bar(
            [
                libqtile.widget.GroupBox(),
            ],
            20
        ),
    )]
    auto_fullscreen = True


class ClientNewStaticConfig(_Config):
    @staticmethod
    def main(c):
        def client_new(c):
            c.static(0)
        libqtile.hook.subscribe.client_new(client_new)


clientnew_config = pytest.mark.parametrize("qtile", [ClientNewStaticConfig], indirect=True)


@clientnew_config
def test_minimal_(qtile):
    self = qtile

    a = self.testWindow("one")
    self.kill_window(a)


@pytest.mark.skipif(whereis("gkrellm") is None, reason="gkrellm not found")
@clientnew_config
def test_gkrellm(qtile):
    qtile.testGkrellm()
    time.sleep(0.1)


class ToGroupConfig(_Config):
    @staticmethod
    def main(c):
        def client_new(c):
            c.togroup("d")
        libqtile.hook.subscribe.client_new(client_new)


togroup_config = pytest.mark.parametrize("qtile", [ToGroupConfig], indirect=True)


@togroup_config
def test_minimal__(qtile):
    qtile.c.group["d"].toscreen()
    qtile.c.group["a"].toscreen()
    a = qtile.testWindow("one")
    assert len(qtile.c.group["d"].info()["windows"]) == 1
    qtile.kill_window(a)


@manager_config
def test_colorPixel(qtile):
    # test for #394
    qtile.c.eval("self.colorPixel(\"ffffff\")")
