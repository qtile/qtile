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

import pytest
import xcffib.xproto
import xcffib.xtest

import libqtile.bar
import libqtile.config
import libqtile.confreader
import libqtile.hook
import libqtile.layout
import libqtile.widget
import libqtile.window
from libqtile.backend.x11 import xcbq
from libqtile.command.client import SelectError
from libqtile.command.interface import CommandError, CommandException
from libqtile.config import Match
from libqtile.confreader import Config
from libqtile.lazy import lazy
from test import conftest
from test.conftest import BareConfig, Retry, no_xinerama


class ManagerConfig(Config):
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
        float_rules=[
            *libqtile.layout.floating.Floating.default_float_rules,
            Match(wm_class='xclock')
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
    screens = [libqtile.config.Screen(
        bottom=libqtile.bar.Bar(
            [
                libqtile.widget.GroupBox(),
            ],
            20
        ),
    )]
    follow_mouse_focus = True


manager_config = pytest.mark.parametrize("manager", [ManagerConfig], indirect=True)


@manager_config
def test_screen_dim(manager):
    manager.test_xclock()
    assert manager.c.screen.info()["index"] == 0
    assert manager.c.screen.info()["x"] == 0
    assert manager.c.screen.info()["width"] == 800
    assert manager.c.group.info()["name"] == 'a'
    assert manager.c.group.info()["focus"] == 'xclock'

    manager.c.to_screen(1)
    manager.test_xeyes()
    assert manager.c.screen.info()["index"] == 1
    assert manager.c.screen.info()["x"] == 800
    assert manager.c.screen.info()["width"] == 640
    assert manager.c.group.info()["name"] == 'b'
    assert manager.c.group.info()["focus"] == 'xeyes'

    manager.c.to_screen(0)
    assert manager.c.screen.info()["index"] == 0
    assert manager.c.screen.info()["x"] == 0
    assert manager.c.screen.info()["width"] == 800
    assert manager.c.group.info()["name"] == 'a'
    assert manager.c.group.info()["focus"] == 'xclock'


@pytest.mark.parametrize("xephyr", [{"xoffset": 0}], indirect=True)
@manager_config
def test_clone_dim(manager):
    manager.test_xclock()
    assert manager.c.screen.info()["index"] == 0
    assert manager.c.screen.info()["x"] == 0
    assert manager.c.screen.info()["width"] == 800
    assert manager.c.group.info()["name"] == 'a'
    assert manager.c.group.info()["focus"] == 'xclock'

    assert len(manager.c.screens()) == 1


@manager_config
def test_to_screen(manager):
    assert manager.c.screen.info()["index"] == 0
    manager.c.to_screen(1)
    assert manager.c.screen.info()["index"] == 1
    manager.test_window("one")
    manager.c.to_screen(0)
    manager.test_window("two")

    ga = manager.c.groups()["a"]
    assert ga["windows"] == ["two"]

    gb = manager.c.groups()["b"]
    assert gb["windows"] == ["one"]

    assert manager.c.window.info()["name"] == "two"
    manager.c.next_screen()
    assert manager.c.window.info()["name"] == "one"
    manager.c.next_screen()
    assert manager.c.window.info()["name"] == "two"
    manager.c.prev_screen()
    assert manager.c.window.info()["name"] == "one"


@manager_config
def test_togroup(manager):
    manager.test_window("one")
    with pytest.raises(CommandError):
        manager.c.window.togroup("nonexistent")
    assert manager.c.groups()["a"]["focus"] == "one"

    manager.c.window.togroup("a")
    assert manager.c.groups()["a"]["focus"] == "one"

    manager.c.window.togroup("b", switch_group=True)
    assert manager.c.groups()["b"]["focus"] == "one"
    assert manager.c.groups()["a"]["focus"] is None
    assert manager.c.group.info()["name"] == "b"

    manager.c.window.togroup("a")
    assert manager.c.groups()["a"]["focus"] == "one"
    assert manager.c.group.info()["name"] == "b"

    manager.c.to_screen(1)
    manager.c.window.togroup("c")
    assert manager.c.groups()["c"]["focus"] == "one"


@manager_config
def test_resize(manager):
    manager.c.screen[0].resize(x=10, y=10, w=100, h=100)

    @Retry(ignore_exceptions=(AssertionError), fail_msg="Screen didn't resize")
    def run():
        d = manager.c.screen[0].info()
        assert d['width'] == 100
        assert d['height'] == 100
        return d
    d = run()
    assert d['x'] == d['y'] == 10


@no_xinerama
def test_minimal(manager):
    assert manager.c.status() == "OK"


@manager_config
@no_xinerama
def test_events(manager):
    assert manager.c.status() == "OK"


# FIXME: failing test disabled. For some reason we don't seem
# to have a keymap in Xnest or Xephyr 99% of the time.
@manager_config
@no_xinerama
def test_keypress(manager):
    manager.test_window("one")
    manager.test_window("two")
    with pytest.raises(CommandError):
        manager.c.simulate_keypress(["unknown"], "j")
    assert manager.c.groups()["a"]["focus"] == "two"
    manager.c.simulate_keypress(["control"], "j")
    assert manager.c.groups()["a"]["focus"] == "one"


class TooFewGroupsConfig(ManagerConfig):
    groups = []


@pytest.mark.parametrize("manager", [TooFewGroupsConfig], indirect=True)
@pytest.mark.parametrize("xephyr", [{"xinerama": True}, {"xinerama": False}], indirect=True)
def test_too_few_groups(manager):
    assert manager.c.groups()
    assert len(manager.c.groups()) == len(manager.c.screens())


class _ChordsConfig(Config):
    groups = [
        libqtile.config.Group("a")
    ]
    layouts = [
        libqtile.layout.max.Max()
    ]
    floating_layout = libqtile.resources.default_config.floating_layout
    keys = [
        libqtile.config.Key(
            [],
            "k",
            lazy.layout.up(),
        ),
        libqtile.config.KeyChord(["control"], "a", [
            libqtile.config.Key(
                [],
                "j",
                lazy.layout.down(),
            )
        ]),
        libqtile.config.KeyChord(["control"], "b", [
            libqtile.config.Key(
                [],
                "j",
                lazy.layout.down(),
            )
        ], "test")
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


chords_config = pytest.mark.parametrize("manager", [_ChordsConfig], indirect=True)


@chords_config
@no_xinerama
def test_immediate_chord(manager):
    manager.test_window("three")
    manager.test_window("two")
    manager.test_window("one")
    assert manager.c.groups()["a"]["focus"] == "one"
    # use normal bind to shift focus up
    manager.c.simulate_keypress([], "k")
    assert manager.c.groups()["a"]["focus"] == "two"
    # enter into key chord and "k" bindin no longer working
    manager.c.simulate_keypress(["control"], "a")
    manager.c.simulate_keypress([], "k")
    assert manager.c.groups()["a"]["focus"] == "two"
    # leave chord using "Escape", "k" bind work again
    manager.c.simulate_keypress([], "Escape")
    manager.c.simulate_keypress([], "k")
    assert manager.c.groups()["a"]["focus"] == "three"
    # enter key chord and use it's "j" binding to shift focus down
    manager.c.simulate_keypress(["control"], "a")
    manager.c.simulate_keypress([], "j")
    assert manager.c.groups()["a"]["focus"] == "two"
    # in immediate chord we leave it after use any
    # bind from it, "j" bind no longer working
    manager.c.simulate_keypress([], "j")
    assert manager.c.groups()["a"]["focus"] == "two"


@chords_config
@no_xinerama
def test_mode_chord(manager):
    manager.test_window("three")
    manager.test_window("two")
    manager.test_window("one")
    assert manager.c.groups()["a"]["focus"] == "one"
    # use normal bind to shift focus up
    manager.c.simulate_keypress([], "k")
    assert manager.c.groups()["a"]["focus"] == "two"
    # enter into key chord and "k" bindin no longer working
    manager.c.simulate_keypress(["control"], "b")
    manager.c.simulate_keypress([], "k")
    assert manager.c.groups()["a"]["focus"] == "two"
    # leave chord using "Escape", "k" bind work again
    manager.c.simulate_keypress([], "Escape")
    manager.c.simulate_keypress([], "k")
    assert manager.c.groups()["a"]["focus"] == "three"
    # enter key chord and use it's "j" binding to shift focus down
    manager.c.simulate_keypress(["control"], "b")
    manager.c.simulate_keypress([], "j")
    assert manager.c.groups()["a"]["focus"] == "two"
    # in mode chord we __not__ leave it after use any
    # bind from it, "j" bind still working
    manager.c.simulate_keypress([], "j")
    assert manager.c.groups()["a"]["focus"] == "one"
    # only way to exit mode chord is by hit "Escape"
    manager.c.simulate_keypress([], "Escape")
    manager.c.simulate_keypress([], "j")
    assert manager.c.groups()["a"]["focus"] == "one"


@manager_config
@no_xinerama
def test_spawn(manager):
    # Spawn something with a pid greater than init's
    assert int(manager.c.spawn("true")) > 1


@manager_config
@no_xinerama
def test_spawn_list(manager):
    # Spawn something with a pid greater than init's
    assert int(manager.c.spawn(["echo", "true"])) > 1


@Retry(ignore_exceptions=(AssertionError,), fail_msg='Window did not die!')
def assert_window_died(client, window_info):
    client.sync()
    wid = window_info['id']
    assert wid not in set([x['id'] for x in client.windows()])


@manager_config
@no_xinerama
def test_kill_window(manager):
    manager.test_window("one")
    window_info = manager.c.window.info()
    manager.c.window[window_info["id"]].kill()
    assert_window_died(manager.c, window_info)


@manager_config
@no_xinerama
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
@no_xinerama
def test_kill_via_message(manager):
    manager.test_window("one")
    window_info = manager.c.window.info()
    conn = xcbq.Connection(manager.display)
    data = xcffib.xproto.ClientMessageData.synthetic([0, 0, 0, 0, 0], "IIIII")
    ev = xcffib.xproto.ClientMessageEvent.synthetic(
        32, window_info["id"], conn.atoms['_NET_CLOSE_WINDOW'], data
    )
    conn.default_screen.root.send_event(ev, mask=xcffib.xproto.EventMask.SubstructureRedirect)
    conn.xsync()
    conn.finalize()
    assert_window_died(manager.c, window_info)


@manager_config
@no_xinerama
def test_change_state_via_message(manager):
    manager.test_window("one")
    window_info = manager.c.window.info()
    conn = xcbq.Connection(manager.display)

    data = xcffib.xproto.ClientMessageData.synthetic([libqtile.window.IconicState, 0, 0, 0, 0], "IIIII")
    ev = xcffib.xproto.ClientMessageEvent.synthetic(
        32, window_info["id"], conn.atoms['WM_CHANGE_STATE'], data
    )
    conn.default_screen.root.send_event(ev, mask=xcffib.xproto.EventMask.SubstructureRedirect)
    conn.xsync()
    assert manager.c.window.info()["minimized"]

    data = xcffib.xproto.ClientMessageData.synthetic([libqtile.window.NormalState, 0, 0, 0, 0], "IIIII")
    ev = xcffib.xproto.ClientMessageEvent.synthetic(
        32, window_info["id"], conn.atoms['WM_CHANGE_STATE'], data
    )
    conn.default_screen.root.send_event(ev, mask=xcffib.xproto.EventMask.SubstructureRedirect)
    conn.xsync()
    assert not manager.c.window.info()["minimized"]

    conn.finalize()


@manager_config
@no_xinerama
def test_regression_groupswitch(manager):
    manager.c.group["c"].toscreen()
    manager.c.group["d"].toscreen()
    assert manager.c.groups()["c"]["screen"] is None


@manager_config
@no_xinerama
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
@no_xinerama
def test_setlayout(manager):
    assert not manager.c.layout.info()["name"] == "max"
    manager.c.group.setlayout("max")
    assert manager.c.layout.info()["name"] == "max"


@manager_config
@no_xinerama
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
@no_xinerama
def test_adddelgroup(manager):
    manager.test_window("one")
    manager.c.addgroup("dummygroup")
    manager.c.addgroup("testgroup")
    assert "testgroup" in manager.c.groups().keys()

    manager.c.window.togroup("testgroup")
    manager.c.delgroup("testgroup")
    assert "testgroup" not in manager.c.groups().keys()
    # Assert that the test window is still a member of some group.
    assert sum(len(i["windows"]) for i in manager.c.groups().values())

    for i in list(manager.c.groups().keys())[:-1]:
        manager.c.delgroup(i)
    with pytest.raises(CommandException):
        manager.c.delgroup(list(manager.c.groups().keys())[0])

    # Assert that setting layout via cmd_addgroup works
    manager.c.addgroup("testgroup2", layout='max')
    assert manager.c.groups()["testgroup2"]['layout'] == 'max'


@manager_config
@no_xinerama
def test_delgroup(manager):
    manager.test_window("one")
    for i in ['a', 'd', 'c']:
        manager.c.delgroup(i)
    with pytest.raises(CommandException):
        manager.c.delgroup('b')


@manager_config
@no_xinerama
def test_nextprevgroup(manager):
    start = manager.c.group.info()["name"]
    ret = manager.c.screen.next_group()
    assert manager.c.group.info()["name"] != start
    assert manager.c.group.info()["name"] == ret
    ret = manager.c.screen.prev_group()
    assert manager.c.group.info()["name"] == start


@manager_config
@no_xinerama
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
@no_xinerama
def test_inspect_xeyes(manager):
    manager.test_xeyes()
    assert manager.c.window.inspect()


@manager_config
@no_xinerama
def test_inspect_xclock(manager):
    manager.test_xclock()
    assert manager.c.window.inspect()["wm_class"]


@manager_config
def test_static(manager):
    manager.test_window("one")
    manager.test_window("two")
    manager.c.window[manager.c.window.info()["id"]].static(
        screen=0, x=10, y=10, width=10, height=10,
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
@no_xinerama
def test_match(manager):
    manager.test_xeyes()
    assert manager.c.window.info()['name'] == 'xeyes'
    assert not manager.c.window.info()['name'] == 'nonexistent'


@manager_config
@no_xinerama
def test_default_float(manager):
    # change to 2 col stack
    manager.c.next_layout()
    assert len(manager.c.layout.info()["stacks"]) == 2
    manager.test_xclock()

    assert manager.c.group.info()['focus'] == 'xclock'
    assert manager.c.window.info()['width'] == 164
    assert manager.c.window.info()['height'] == 164
    assert manager.c.window.info()['x'] == 318
    assert manager.c.window.info()['y'] == 208
    assert manager.c.window.info()['floating'] is True

    manager.c.window.move_floating(10, 20)
    assert manager.c.window.info()['width'] == 164
    assert manager.c.window.info()['height'] == 164
    assert manager.c.window.info()['x'] == 328
    assert manager.c.window.info()['y'] == 228
    assert manager.c.window.info()['floating'] is True

    manager.c.window.set_position_floating(10, 20)
    assert manager.c.window.info()['width'] == 164
    assert manager.c.window.info()['height'] == 164
    assert manager.c.window.info()['x'] == 10
    assert manager.c.window.info()['y'] == 20
    assert manager.c.window.info()['floating'] is True

    w = None
    conn = xcbq.Connection(manager.display)

    def size_hints():
        nonlocal w
        w = conn.create_window(5, 5, 10, 10)

        # set the size hints
        hints = [0] * 18
        hints[0] = xcbq.NormalHintsFlags["PMinSize"] | xcbq.NormalHintsFlags["PMaxSize"]
        hints[5] = hints[6] = hints[7] = hints[8] = 10
        w.set_property("WM_NORMAL_HINTS", hints, type="WM_SIZE_HINTS", format=32)
        w.map()
        conn.conn.flush()

    try:
        manager.create_window(size_hints)
        assert manager.c.window.info()['floating'] is True
    finally:
        w.kill_client()
        conn.finalize()


@manager_config
@no_xinerama
def test_last_float_size(manager):
    """
    When you re-float something it would be preferable to have it use the previous float size
    """
    manager.test_xeyes()
    assert manager.c.window.info()['name'] == 'xeyes'
    assert manager.c.window.info()['width'] == 798
    assert manager.c.window.info()['height'] == 578
    # float and it moves
    manager.c.window.toggle_floating()
    assert manager.c.window.info()['width'] == 150
    assert manager.c.window.info()['height'] == 100
    # resize
    manager.c.window.set_size_floating(50, 90)
    assert manager.c.window.info()['width'] == 50
    assert manager.c.window.info()['height'] == 90
    # back to not floating
    manager.c.window.toggle_floating()
    assert manager.c.window.info()['width'] == 798
    assert manager.c.window.info()['height'] == 578
    # float again, should use last float size
    manager.c.window.toggle_floating()
    assert manager.c.window.info()['width'] == 50
    assert manager.c.window.info()['height'] == 90

    # make sure it works through min and max
    manager.c.window.toggle_maximize()
    manager.c.window.toggle_minimize()
    manager.c.window.toggle_minimize()
    manager.c.window.toggle_floating()
    assert manager.c.window.info()['width'] == 50
    assert manager.c.window.info()['height'] == 90


@manager_config
@no_xinerama
def test_float_max_min_combo(manager):
    # change to 2 col stack
    manager.c.next_layout()
    assert len(manager.c.layout.info()["stacks"]) == 2
    manager.test_xcalc()
    manager.test_xeyes()

    assert manager.c.group.info()['focus'] == 'xeyes'
    assert manager.c.window.info()['width'] == 398
    assert manager.c.window.info()['height'] == 578
    assert manager.c.window.info()['x'] == 400
    assert manager.c.window.info()['y'] == 0
    assert manager.c.window.info()['floating'] is False

    manager.c.window.toggle_maximize()
    assert manager.c.window.info()['floating'] is True
    assert manager.c.window.info()['maximized'] is True
    assert manager.c.window.info()['width'] == 800
    assert manager.c.window.info()['height'] == 580
    assert manager.c.window.info()['x'] == 0
    assert manager.c.window.info()['y'] == 0

    manager.c.window.toggle_minimize()
    assert manager.c.group.info()['focus'] == 'xeyes'
    assert manager.c.window.info()['floating'] is True
    assert manager.c.window.info()['minimized'] is True
    assert manager.c.window.info()['width'] == 800
    assert manager.c.window.info()['height'] == 580
    assert manager.c.window.info()['x'] == 0
    assert manager.c.window.info()['y'] == 0

    manager.c.window.toggle_floating()
    assert manager.c.group.info()['focus'] == 'xeyes'
    assert manager.c.window.info()['floating'] is False
    assert manager.c.window.info()['minimized'] is False
    assert manager.c.window.info()['maximized'] is False
    assert manager.c.window.info()['width'] == 398
    assert manager.c.window.info()['height'] == 578
    assert manager.c.window.info()['x'] == 400
    assert manager.c.window.info()['y'] == 0


@manager_config
@no_xinerama
def test_toggle_fullscreen(manager):
    # change to 2 col stack
    manager.c.next_layout()
    assert len(manager.c.layout.info()["stacks"]) == 2
    manager.test_xcalc()
    manager.test_xeyes()

    assert manager.c.group.info()['focus'] == 'xeyes'
    assert manager.c.window.info()['width'] == 398
    assert manager.c.window.info()['height'] == 578
    assert manager.c.window.info()['float_info'] == {
        'y': 0, 'x': 400, 'width': 150, 'height': 100}
    assert manager.c.window.info()['x'] == 400
    assert manager.c.window.info()['y'] == 0

    manager.c.window.toggle_fullscreen()
    assert manager.c.window.info()['floating'] is True
    assert manager.c.window.info()['maximized'] is False
    assert manager.c.window.info()['fullscreen'] is True
    assert manager.c.window.info()['width'] == 800
    assert manager.c.window.info()['height'] == 600
    assert manager.c.window.info()['x'] == 0
    assert manager.c.window.info()['y'] == 0

    manager.c.window.toggle_fullscreen()
    assert manager.c.window.info()['floating'] is False
    assert manager.c.window.info()['maximized'] is False
    assert manager.c.window.info()['fullscreen'] is False
    assert manager.c.window.info()['width'] == 398
    assert manager.c.window.info()['height'] == 578
    assert manager.c.window.info()['x'] == 400
    assert manager.c.window.info()['y'] == 0


@manager_config
@no_xinerama
def test_toggle_max(manager):
    # change to 2 col stack
    manager.c.next_layout()
    assert len(manager.c.layout.info()["stacks"]) == 2
    manager.test_xcalc()
    manager.test_xeyes()

    assert manager.c.group.info()['focus'] == 'xeyes'
    assert manager.c.window.info()['width'] == 398
    assert manager.c.window.info()['height'] == 578
    assert manager.c.window.info()['float_info'] == {
        'y': 0, 'x': 400, 'width': 150, 'height': 100}
    assert manager.c.window.info()['x'] == 400
    assert manager.c.window.info()['y'] == 0

    manager.c.window.toggle_maximize()
    assert manager.c.window.info()['floating'] is True
    assert manager.c.window.info()['maximized'] is True
    assert manager.c.window.info()['width'] == 800
    assert manager.c.window.info()['height'] == 580
    assert manager.c.window.info()['x'] == 0
    assert manager.c.window.info()['y'] == 0

    manager.c.window.toggle_maximize()
    assert manager.c.window.info()['floating'] is False
    assert manager.c.window.info()['maximized'] is False
    assert manager.c.window.info()['width'] == 398
    assert manager.c.window.info()['height'] == 578
    assert manager.c.window.info()['x'] == 400
    assert manager.c.window.info()['y'] == 0


@manager_config
@no_xinerama
def test_toggle_min(manager):
    # change to 2 col stack
    manager.c.next_layout()
    assert len(manager.c.layout.info()["stacks"]) == 2
    manager.test_xcalc()
    manager.test_xeyes()

    assert manager.c.group.info()['focus'] == 'xeyes'
    assert manager.c.window.info()['width'] == 398
    assert manager.c.window.info()['height'] == 578
    assert manager.c.window.info()['float_info'] == {
        'y': 0, 'x': 400, 'width': 150, 'height': 100}
    assert manager.c.window.info()['x'] == 400
    assert manager.c.window.info()['y'] == 0

    manager.c.window.toggle_minimize()
    assert manager.c.group.info()['focus'] == 'xeyes'
    assert manager.c.window.info()['floating'] is True
    assert manager.c.window.info()['minimized'] is True
    assert manager.c.window.info()['width'] == 398
    assert manager.c.window.info()['height'] == 578
    assert manager.c.window.info()['x'] == 400
    assert manager.c.window.info()['y'] == 0

    manager.c.window.toggle_minimize()
    assert manager.c.group.info()['focus'] == 'xeyes'
    assert manager.c.window.info()['floating'] is False
    assert manager.c.window.info()['minimized'] is False
    assert manager.c.window.info()['width'] == 398
    assert manager.c.window.info()['height'] == 578
    assert manager.c.window.info()['x'] == 400
    assert manager.c.window.info()['y'] == 0


@manager_config
@no_xinerama
def test_toggle_floating(manager):
    manager.test_xeyes()
    assert manager.c.window.info()['floating'] is False
    manager.c.window.toggle_floating()
    assert manager.c.window.info()['floating'] is True
    manager.c.window.toggle_floating()
    assert manager.c.window.info()['floating'] is False
    manager.c.window.toggle_floating()
    assert manager.c.window.info()['floating'] is True

    # change layout (should still be floating)
    manager.c.next_layout()
    assert manager.c.window.info()['floating'] is True


@manager_config
@no_xinerama
def test_floating_focus(manager):
    # change to 2 col stack
    manager.c.next_layout()
    assert len(manager.c.layout.info()["stacks"]) == 2
    manager.test_xcalc()
    manager.test_xeyes()
    # manager.test_window("one")
    assert manager.c.window.info()['width'] == 398
    assert manager.c.window.info()['height'] == 578
    manager.c.window.toggle_floating()
    manager.c.window.move_floating(10, 20)
    assert manager.c.window.info()['name'] == 'xeyes'
    assert manager.c.group.info()['focus'] == 'xeyes'
    # check what stack thinks is focus
    assert [x['current'] for x in manager.c.layout.info()['stacks']] == [0, 0]

    # change focus to xcalc
    manager.c.group.next_window()
    assert manager.c.window.info()['width'] == 398
    assert manager.c.window.info()['height'] == 578
    assert manager.c.window.info()['name'] != 'xeyes'
    assert manager.c.group.info()['focus'] != 'xeyes'
    # check what stack thinks is focus
    # check what stack thinks is focus
    assert [x['current'] for x in manager.c.layout.info()['stacks']] == [0, 0]

    # focus back to xeyes
    manager.c.group.next_window()
    assert manager.c.window.info()['name'] == 'xeyes'
    # check what stack thinks is focus
    assert [x['current'] for x in manager.c.layout.info()['stacks']] == [0, 0]

    # now focusing via layout is borked (won't go to float)
    manager.c.layout.up()
    assert manager.c.window.info()['name'] != 'xeyes'
    manager.c.layout.up()
    assert manager.c.window.info()['name'] != 'xeyes'
    # check what stack thinks is focus
    assert [x['current'] for x in manager.c.layout.info()['stacks']] == [0, 0]

    # focus back to xeyes
    manager.c.group.next_window()
    assert manager.c.window.info()['name'] == 'xeyes'
    # check what stack thinks is focus
    assert [x['current'] for x in manager.c.layout.info()['stacks']] == [0, 0]


@manager_config
@no_xinerama
def test_move_floating(manager):
    manager.test_xeyes()
    # manager.test_window("one")
    assert manager.c.window.info()['width'] == 798
    assert manager.c.window.info()['height'] == 578

    assert manager.c.window.info()['x'] == 0
    assert manager.c.window.info()['y'] == 0
    manager.c.window.toggle_floating()
    assert manager.c.window.info()['floating'] is True

    manager.c.window.move_floating(10, 20)
    assert manager.c.window.info()['width'] == 150
    assert manager.c.window.info()['height'] == 100
    assert manager.c.window.info()['x'] == 10
    assert manager.c.window.info()['y'] == 20

    manager.c.window.set_size_floating(50, 90)
    assert manager.c.window.info()['width'] == 50
    assert manager.c.window.info()['height'] == 90
    assert manager.c.window.info()['x'] == 10
    assert manager.c.window.info()['y'] == 20

    manager.c.window.resize_floating(10, 20)
    assert manager.c.window.info()['width'] == 60
    assert manager.c.window.info()['height'] == 110
    assert manager.c.window.info()['x'] == 10
    assert manager.c.window.info()['y'] == 20

    manager.c.window.set_size_floating(10, 20)
    assert manager.c.window.info()['width'] == 10
    assert manager.c.window.info()['height'] == 20
    assert manager.c.window.info()['x'] == 10
    assert manager.c.window.info()['y'] == 20

    # change layout (x, y should be same)
    manager.c.next_layout()
    assert manager.c.window.info()['width'] == 10
    assert manager.c.window.info()['height'] == 20
    assert manager.c.window.info()['x'] == 10
    assert manager.c.window.info()['y'] == 20


@manager_config
@no_xinerama
def test_screens(manager):
    assert len(manager.c.screens())


@manager_config
@no_xinerama
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

    assert manager.c.window.info()['name'] == 'one'


@pytest.mark.parametrize("manager", [BareConfig, ManagerConfig], indirect=True)
@pytest.mark.parametrize("xephyr", [{"xinerama": True}, {"xinerama": False}], indirect=True)
def test_xeyes(manager):
    manager.test_xeyes()


@pytest.mark.parametrize("manager", [BareConfig, ManagerConfig], indirect=True)
@pytest.mark.parametrize("xephyr", [{"xinerama": True}, {"xinerama": False}], indirect=True)
def test_xcalc(manager):
    manager.test_xcalc()


@pytest.mark.parametrize("manager", [BareConfig, ManagerConfig], indirect=True)
@pytest.mark.parametrize("xephyr", [{"xinerama": True}, {"xinerama": False}], indirect=True)
def test_xcalc_kill_window(manager):
    manager.test_xcalc()
    window_info = manager.c.window.info()
    manager.c.window.kill()
    assert_window_died(manager.c, window_info)


@pytest.mark.parametrize("manager", [BareConfig, ManagerConfig], indirect=True)
@pytest.mark.parametrize("xephyr", [{"xinerama": True}, {"xinerama": False}], indirect=True)
def test_map_request(manager):
    manager.test_window("one")
    info = manager.c.groups()["a"]
    assert "one" in info["windows"]
    assert info["focus"] == "one"

    manager.test_window("two")
    info = manager.c.groups()["a"]
    assert "two" in info["windows"]
    assert info["focus"] == "two"


@pytest.mark.parametrize("manager", [BareConfig, ManagerConfig], indirect=True)
@pytest.mark.parametrize("xephyr", [{"xinerama": True}, {"xinerama": False}], indirect=True)
def test_unmap(manager):
    one = manager.test_window("one")
    two = manager.test_window("two")
    three = manager.test_window("three")
    info = manager.c.groups()["a"]
    assert info["focus"] == "three"

    assert len(manager.c.windows()) == 3
    manager.kill_window(three)

    assert len(manager.c.windows()) == 2
    info = manager.c.groups()["a"]
    assert info["focus"] == "two"

    manager.kill_window(two)
    assert len(manager.c.windows()) == 1
    info = manager.c.groups()["a"]
    assert info["focus"] == "one"

    manager.kill_window(one)
    assert len(manager.c.windows()) == 0
    info = manager.c.groups()["a"]
    assert info["focus"] is None


@pytest.mark.parametrize("manager", [BareConfig, ManagerConfig], indirect=True)
@pytest.mark.parametrize("xephyr", [{"xinerama": True}, {"xinerama": False}], indirect=True)
def test_setgroup(manager):
    manager.test_window("one")
    manager.c.group["b"].toscreen()
    manager.groupconsistency()
    if len(manager.c.screens()) == 1:
        assert manager.c.groups()["a"]["screen"] is None
    else:
        assert manager.c.groups()["a"]["screen"] == 1
    assert manager.c.groups()["b"]["screen"] == 0

    manager.c.group["c"].toscreen()
    manager.groupconsistency()
    assert manager.c.groups()["c"]["screen"] == 0

    # Setting the current group once again switches back to the previous group
    manager.c.group["c"].toscreen()
    manager.groupconsistency()
    assert manager.c.group.info()["name"] == "b"


@pytest.mark.parametrize("manager", [BareConfig, ManagerConfig], indirect=True)
@pytest.mark.parametrize("xephyr", [{"xinerama": True}, {"xinerama": False}], indirect=True)
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
    assert manager.c.groups()["a"]["focus"] == "one"


class TScreen(libqtile.config.Screen):
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


class _Config(Config):
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
    floating_layout = libqtile.resources.default_config.floating_layout
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
            c.cmd_static(0)
        libqtile.hook.subscribe.client_new(client_new)


clientnew_config = pytest.mark.parametrize("manager", [ClientNewStaticConfig], indirect=True)


@clientnew_config
def test_clientnew_config(manager):
    a = manager.test_window("one")
    manager.kill_window(a)


class ToGroupConfig(_Config):
    @staticmethod
    def main(c):
        def client_new(c):
            c.togroup("d")
        libqtile.hook.subscribe.client_new(client_new)


togroup_config = pytest.mark.parametrize("manager", [ToGroupConfig], indirect=True)


@togroup_config
def test_togroup_config(manager):
    manager.c.group["d"].toscreen()
    manager.c.group["a"].toscreen()
    a = manager.test_window("one")
    assert len(manager.c.group["d"].info()["windows"]) == 1
    manager.kill_window(a)


@manager_config
def test_color_pixel(manager):
    (success, e) = manager.c.eval("self.conn.color_pixel(\"ffffff\")")
    assert success, e


@manager_config
def test_change_loglevel(manager):
    assert manager.c.loglevel() == logging.INFO
    assert manager.c.loglevelname() == 'INFO'
    manager.c.debug()
    assert manager.c.loglevel() == logging.DEBUG
    assert manager.c.loglevelname() == 'DEBUG'
    manager.c.info()
    assert manager.c.loglevel() == logging.INFO
    assert manager.c.loglevelname() == 'INFO'
    manager.c.warning()
    assert manager.c.loglevel() == logging.WARNING
    assert manager.c.loglevelname() == 'WARNING'
    manager.c.error()
    assert manager.c.loglevel() == logging.ERROR
    assert manager.c.loglevelname() == 'ERROR'
    manager.c.critical()
    assert manager.c.loglevel() == logging.CRITICAL
    assert manager.c.loglevelname() == 'CRITICAL'


@manager_config
def test_user_position(manager):
    w = None
    conn = xcbq.Connection(manager.display)

    def user_position_window():
        nonlocal w
        w = conn.create_window(5, 5, 10, 10)
        # manager config automatically floats xclock
        w.set_property("WM_CLASS", "xclock", type="STRING", format=8)
        # set the user specified position flag
        hints = [0] * 18
        hints[0] = xcbq.NormalHintsFlags["USPosition"]
        w.set_property("WM_NORMAL_HINTS", hints, type="WM_SIZE_HINTS", format=32)
        w.map()
        conn.conn.flush()
    try:
        manager.create_window(user_position_window)
        assert manager.c.window.info()['floating'] is True
        assert manager.c.window.info()['x'] == 5
        assert manager.c.window.info()['y'] == 5
        assert manager.c.window.info()['width'] == 10
        assert manager.c.window.info()['height'] == 10
    finally:
        w.kill_client()
        conn.finalize()


def wait_for_focus_events(conn):
    got_take_focus = False
    got_focus_in = False
    while True:
        event = conn.conn.poll_for_event()
        if not event:
            break

        if (isinstance(event, xcffib.xproto.ClientMessageEvent) and
                event.type != conn.atoms["WM_TAKE_FOCUS"]):
            got_take_focus = True

        if isinstance(event, xcffib.xproto.FocusInEvent):
            got_focus_in = True
    return got_take_focus, got_focus_in


@manager_config
def test_only_one_focus(manager):
    w = None
    conn = xcbq.Connection(manager.display)

    def both_wm_take_focus_and_input_hint():
        nonlocal w
        w = conn.create_window(5, 5, 10, 10)
        w.set_attribute(eventmask=xcffib.xproto.EventMask.FocusChange)
        # manager config automatically floats xclock
        w.set_property("WM_CLASS", "xclock", type="STRING", format=8)

        # set both the input hit
        hints = [0] * 14
        hints[0] = xcbq.HintsFlags["InputHint"]
        hints[1] = 1  # set hints to 1, i.e. we want them
        w.set_property("WM_HINTS", hints, type="WM_HINTS", format=32)

        # and add the WM_PROTOCOLS protocol WM_TAKE_FOCUS
        conn.conn.core.ChangePropertyChecked(
            xcffib.xproto.PropMode.Append,
            w.wid,
            conn.atoms["WM_PROTOCOLS"],
            conn.atoms["ATOM"],
            32,
            1,
            [conn.atoms["WM_TAKE_FOCUS"]],
        ).check()

        w.map()
        conn.conn.flush()
    try:
        manager.create_window(both_wm_take_focus_and_input_hint)
        assert manager.c.window.info()['floating'] is True
        got_take_focus, got_focus_in = wait_for_focus_events(conn)
        assert not got_take_focus
        assert got_focus_in
    finally:
        w.kill_client()
        conn.finalize()


@manager_config
def test_only_wm_protocols_focus(manager):
    w = None
    conn = xcbq.Connection(manager.display)

    def only_wm_protocols_focus():
        nonlocal w
        w = conn.create_window(5, 5, 10, 10)
        w.set_attribute(eventmask=xcffib.xproto.EventMask.FocusChange)
        # manager config automatically floats xclock
        w.set_property("WM_CLASS", "xclock", type="STRING", format=8)

        hints = [0] * 14
        hints[0] = xcbq.HintsFlags["InputHint"]
        hints[1] = 0  # set hints to 0, i.e. we don't want them
        w.set_property("WM_HINTS", hints, type="WM_HINTS", format=32)

        # add the WM_PROTOCOLS protocol WM_TAKE_FOCUS
        conn.conn.core.ChangePropertyChecked(
            xcffib.xproto.PropMode.Append,
            w.wid,
            conn.atoms["WM_PROTOCOLS"],
            conn.atoms["ATOM"],
            32,
            1,
            [conn.atoms["WM_TAKE_FOCUS"]],
        ).check()

        w.map()
        conn.conn.flush()
    try:
        manager.create_window(only_wm_protocols_focus)
        assert manager.c.window.info()['floating'] is True
        got_take_focus, got_focus_in = wait_for_focus_events(conn)
        assert got_take_focus
        assert not got_focus_in
    finally:
        w.kill_client()
        conn.finalize()


@manager_config
def test_only_input_hint_focus(manager):
    w = None
    conn = xcbq.Connection(manager.display)

    def only_input_hint():
        nonlocal w
        w = conn.create_window(5, 5, 10, 10)
        w.set_attribute(eventmask=xcffib.xproto.EventMask.FocusChange)
        # manager config automatically floats xclock
        w.set_property("WM_CLASS", "xclock", type="STRING", format=8)

        # set the input hint
        hints = [0] * 14
        hints[0] = xcbq.HintsFlags["InputHint"]
        hints[1] = 1  # set hints to 1, i.e. we want them
        w.set_property("WM_HINTS", hints, type="WM_HINTS", format=32)

        w.map()
        conn.conn.flush()
    try:
        manager.create_window(only_input_hint)
        assert manager.c.window.info()['floating'] is True
        got_take_focus, got_focus_in = wait_for_focus_events(conn)
        assert not got_take_focus
        assert got_focus_in
    finally:
        w.kill_client()
        conn.finalize()


@manager_config
def test_no_focus(manager):
    w = None
    conn = xcbq.Connection(manager.display)

    def no_focus():
        nonlocal w
        w = conn.create_window(5, 5, 10, 10)
        w.set_attribute(eventmask=xcffib.xproto.EventMask.FocusChange)
        # manager config automatically floats xclock
        w.set_property("WM_CLASS", "xclock", type="STRING", format=8)

        hints = [0] * 14
        hints[0] = xcbq.HintsFlags["InputHint"]
        w.set_property("WM_HINTS", hints, type="WM_HINTS", format=32)
        w.map()
        conn.conn.flush()
    try:
        manager.create_window(no_focus)
        assert manager.c.window.info()['floating'] is True
        got_take_focus, got_focus_in = wait_for_focus_events(conn)
        assert not got_take_focus
        assert not got_focus_in
    finally:
        w.kill_client()
        conn.finalize()


@manager_config
def test_hints_setting_unsetting(manager):
    w = None
    conn = xcbq.Connection(manager.display)

    def no_input_hint():
        nonlocal w
        w = conn.create_window(5, 5, 10, 10)
        w.map()
        conn.conn.flush()

    try:
        manager.create_window(no_input_hint)
        # We default the input hint to true since some non-trivial number of
        # windows don't set it, and most of them want focus. The spec allows
        # WMs to assume "convenient" values.
        assert manager.c.window.hints()['input']

        # now try to "update" it, but don't really set an update (i.e. the
        # InputHint bit is 0, so the WM should not derive a new hint from the
        # content of the message at the input hint's offset)
        hints = [0] * 14
        w.set_property("WM_HINTS", hints, type="WM_HINTS", format=32)
        conn.flush()

        # should still have the hint
        assert manager.c.window.hints()['input']

        # now do an update: turn it off
        hints[0] = xcbq.HintsFlags["InputHint"]
        hints[1] = 0
        w.set_property("WM_HINTS", hints, type="WM_HINTS", format=32)
        conn.flush()
        assert not manager.c.window.hints()['input']

        # turn it back on
        hints[0] = xcbq.HintsFlags["InputHint"]
        hints[1] = 1
        w.set_property("WM_HINTS", hints, type="WM_HINTS", format=32)
        conn.flush()
        assert manager.c.window.hints()['input']

    finally:
        w.kill_client()
        conn.finalize()


@manager_config
def test_strut_handling(manager):
    w = None
    conn = xcbq.Connection(manager.display)

    def has_struts():
        nonlocal w
        w = conn.create_window(0, 0, 10, 10)
        w.set_property("_NET_WM_STRUT", [0, 0, 0, 10])
        w.map()
        conn.conn.flush()

    def test_initial_state():
        assert manager.c.window.info()['width'] == 798
        assert manager.c.window.info()['height'] == 578
        assert manager.c.window.info()['x'] == 0
        assert manager.c.window.info()['y'] == 0
        bar_id = manager.c.bar["bottom"].info()["window"]
        bar = manager.c.window[bar_id].info()
        assert bar["height"] == 20
        assert bar["y"] == 580

    manager.test_xcalc()
    test_initial_state()

    try:
        manager.create_window(has_struts)
        manager.c.window.static(0, None, None, None, None)
        assert manager.c.window.info()['width'] == 798
        assert manager.c.window.info()['height'] == 568
        assert manager.c.window.info()['x'] == 0
        assert manager.c.window.info()['y'] == 0
        bar_id = manager.c.bar["bottom"].info()["window"]
        bar = manager.c.window[bar_id].info()
        assert bar["height"] == 20
        assert bar["y"] == 570

    finally:
        w.kill_client()
        conn.finalize()

    test_initial_state()


class BringFrontClickConfig(ManagerConfig):
    bring_front_click = True


class BringFrontClickFloatingOnlyConfig(ManagerConfig):
    bring_front_click = "floating_only"


@pytest.fixture
def bring_front_click(request):
    return request.param


@pytest.mark.parametrize(
    "manager, bring_front_click",
    [
        (ManagerConfig, False),
        (BringFrontClickConfig, True),
        (BringFrontClickFloatingOnlyConfig, "floating_only"),
    ],
    indirect=True,
)
def test_bring_front_click(manager, bring_front_click):
    def get_all_windows(conn):
        root = conn.default_screen.root.wid
        q = conn.conn.core.QueryTree(root).reply()
        return list(q.children)

    def fake_click(conn, xtest, x, y):
        root = conn.default_screen.root.wid
        xtest.FakeInput(6, 0, xcffib.xproto.Time.CurrentTime, root, x, y, 0)
        xtest.FakeInput(4, 1, xcffib.xproto.Time.CurrentTime, root, 0, 0, 0)
        xtest.FakeInput(5, 1, xcffib.xproto.Time.CurrentTime, root, 0, 0, 0)
        conn.conn.flush()

    conn = xcbq.Connection(manager.display)
    xtest = conn.conn(xcffib.xtest.key)

    # this is a tiled window.
    manager.test_window("one")
    manager.c.sync()

    manager.test_window("two")
    manager.c.window.set_position_floating(50, 50)
    manager.c.window.set_size_floating(50, 50)
    manager.c.sync()

    manager.test_window("three")
    manager.c.window.set_position_floating(150, 50)
    manager.c.window.set_size_floating(50, 50)
    manager.c.sync()

    wids = [x["id"] for x in manager.c.windows()]
    names = [x["name"] for x in manager.c.windows()]

    assert names == ["one", "two", "three"]
    wins = get_all_windows(conn)
    assert wins.index(wids[0]) < wins.index(wids[1]) < wins.index(wids[2])

    # Click on window two
    fake_click(conn, xtest, 55, 55)
    manager.c.sync()
    wins = get_all_windows(conn)
    if bring_front_click:
        assert wins.index(wids[0]) < wins.index(wids[2]) < wins.index(wids[1])
    else:
        assert wins.index(wids[0]) < wins.index(wids[1]) < wins.index(wids[2])

    # Click on window one
    fake_click(conn, xtest, 10, 10)
    manager.c.sync()
    wins = get_all_windows(conn)
    if bring_front_click == "floating_only":
        assert wins.index(wids[0]) < wins.index(wids[2]) < wins.index(wids[1])
    elif bring_front_click:
        assert wins.index(wids[2]) < wins.index(wids[1]) < wins.index(wids[0])
    else:
        assert wins.index(wids[0]) < wins.index(wids[1]) < wins.index(wids[2])


class CursorWarpConfig(ManagerConfig):
    cursor_warp = "floating_only"
    screens = [
        libqtile.config.Screen(
            bottom=libqtile.bar.Bar(
                [
                    libqtile.widget.GroupBox(),
                ],
                20,
            ),
        ),
        libqtile.config.Screen(
            bottom=libqtile.bar.Bar(
                [
                    libqtile.widget.GroupBox(),
                ],
                20,
            ),
        ),
    ]


@pytest.mark.parametrize(
    "manager",
    [CursorWarpConfig],
    indirect=True,
)
def test_cursor_warp(manager):
    conn = xcbq.Connection(manager.display)
    root = conn.default_screen.root.wid

    assert manager.c.screen.info()["index"] == 0

    manager.test_window("one")
    manager.c.window.set_position_floating(50, 50)
    manager.c.window.set_size_floating(50, 50)

    manager.c.to_screen(1)
    assert manager.c.screen.info()["index"] == 1

    p = conn.conn.core.QueryPointer(root).reply()
    # Here pointer should warp to the second screen as there are no windows
    # there.
    assert p.root_x == conftest.WIDTH + conftest.SECOND_WIDTH // 2
    # Reduce the bar height from the screen height.
    assert p.root_y == (conftest.SECOND_HEIGHT - 20) // 2

    manager.c.to_screen(0)
    assert manager.c.window.info()["name"] == "one"

    p = conn.conn.core.QueryPointer(manager.c.window.info()["id"]).reply()

    # Here pointer should warp to the window.
    assert p.win_x == 25
    assert p.win_y == 25
    assert p.same_screen
