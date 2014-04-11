import os
import time
import cStringIO
import subprocess
import signal
import libqtile
import libqtile.layout
import libqtile.bar
import libqtile.command
import libqtile.widget
import libqtile.manager
import libqtile.config
import libqtile.hook
import libqtile.confreader
import utils
from utils import Xephyr
from nose.tools import assert_raises
from nose.plugins.attrib import attr


class TestConfig:
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


class BareConfig:
    auto_fullscreen = True
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
    screens = [libqtile.config.Screen()]
    main = None
    follow_mouse_focus = False


@Xephyr(True, TestConfig())
def test_screen_dim(self):
    #self.c.restart()
    self.testXclock()
    assert self.c.screen.info()["index"] == 0
    assert self.c.screen.info()["x"] == 0
    assert self.c.screen.info()["width"] == 800
    assert self.c.group.info()["name"] == 'a'
    assert self.c.group.info()["focus"] == 'xclock'

    self.c.to_screen(1)
    self.testXeyes()
    assert self.c.screen.info()["index"] == 1
    assert self.c.screen.info()["x"] == 800
    assert self.c.screen.info()["width"] == 640
    assert self.c.group.info()["name"] == 'b'
    assert self.c.group.info()["focus"] == 'xeyes'

    self.c.to_screen(0)
    assert self.c.screen.info()["index"] == 0
    assert self.c.screen.info()["x"] == 0
    assert self.c.screen.info()["width"] == 800
    assert self.c.group.info()["name"] == 'a'
    assert self.c.group.info()["focus"] == 'xclock'


@Xephyr(True, TestConfig(), xoffset=0)
def test_clone_dim(self):
    self.testXclock()
    assert self.c.screen.info()["index"] == 0
    assert self.c.screen.info()["x"] == 0
    assert self.c.screen.info()["width"] == 800
    assert self.c.group.info()["name"] == 'a'
    assert self.c.group.info()["focus"] == 'xclock'

    assert len(self.c.screens()) == 1


@Xephyr(True, TestConfig())
def test_to_screen(self):
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
    self.c.to_next_screen()
    assert self.c.window.info()["name"] == "one"
    self.c.to_next_screen()
    assert self.c.window.info()["name"] == "two"
    self.c.to_prev_screen()
    assert self.c.window.info()["name"] == "one"


@Xephyr(True, TestConfig())
def test_togroup(self):
    self.testWindow("one")
    assert_raises(libqtile.command.CommandError,
                  self.c.window.togroup, "nonexistent")
    assert self.c.groups()["a"]["focus"] == "one"
    self.c.window.togroup("a")
    assert self.c.groups()["a"]["focus"] == "one"
    self.c.window.togroup("b")
    assert self.c.groups()["b"]["focus"] == "one"
    assert self.c.groups()["a"]["focus"] == None
    self.c.to_screen(1)
    self.c.window.togroup("c")
    assert self.c.groups()["c"]["focus"] == "one"


@Xephyr(True, TestConfig())
def test_resize(self):
    self.c.screen[0].resize(x=10, y=10, w=100, h=100)
    d = self.c.screen[0].info()
    assert d["width"] == d["height"] == 100
    assert d["x"] == d["y"] == 10


@Xephyr(False, BareConfig())
def test_minimal(self):
    assert self.c.status() == "OK"


@Xephyr(False, TestConfig())
def test_events(self):
    assert self.c.status() == "OK"


# FIXME: failing test disabled. For some reason we don't seem
# to have a keymap in Xnest or Xephyr 99% of the time.
@Xephyr(False, TestConfig())
def test_keypress(self):
    self.testWindow("one")
    self.testWindow("two")
    v = self.c.simulate_keypress(["unknown"], "j")
    assert v.startswith("Unknown modifier")
    assert self.c.groups()["a"]["focus"] == "two"
    self.c.simulate_keypress(["control"], "j")
    assert self.c.groups()["a"]["focus"] == "one"


@Xephyr(False, TestConfig())
def test_spawn(self):
    assert self.c.spawn("true") == None


@Xephyr(False, TestConfig())
def test_kill(self):
    self.testWindow("one")
    self.testwindows = []
    self.c.window[self.c.window.info()["id"]].kill()
    self.c.sync()
    for i in range(20):
        if len(self.c.windows()) == 0:
            break
        time.sleep(0.1)
    else:
        raise AssertionError("Window did not die...")


@Xephyr(False, TestConfig())
def test_regression_groupswitch(self):
    self.c.group["c"].toscreen()
    self.c.group["d"].toscreen()
    assert self.c.groups()["c"]["screen"] == None


@Xephyr(False, TestConfig())
def test_nextlayout(self):
    self.testWindow("one")
    self.testWindow("two")
    assert len(self.c.layout.info()["stacks"]) == 1
    self.c.nextlayout()
    assert len(self.c.layout.info()["stacks"]) == 2
    self.c.nextlayout()
    self.c.nextlayout()
    assert len(self.c.layout.info()["stacks"]) == 1


@Xephyr(False, TestConfig())
def test_setlayout(self):
    assert not self.c.layout.info()["name"] == "max"
    self.c.group.setlayout("max")
    assert self.c.layout.info()["name"] == "max"


@Xephyr(False, TestConfig())
def test_adddelgroup(self):
    self.testWindow("one")
    self.c.addgroup("dummygroup")
    self.c.addgroup("testgroup")
    assert "testgroup" in self.c.groups().keys()
    self.c.window.togroup("testgroup")
    self.c.delgroup("testgroup")
    assert not "testgroup" in self.c.groups().keys()
    # Assert that the test window is still a member of some group.
    assert sum([len(i["windows"]) for i in self.c.groups().values()])
    for i in self.c.groups().keys()[:len(self.c.groups())-1]:
        self.c.delgroup(i)
    assert_raises(libqtile.command.CommandException,
                  self.c.delgroup, self.c.groups().keys()[0])


@Xephyr(False, TestConfig())
def test_nextprevgroup(self):
    start = self.c.group.info()["name"]
    ret = self.c.screen.nextgroup()
    assert self.c.group.info()["name"] != start
    assert self.c.group.info()["name"] == ret
    ret = self.c.screen.prevgroup()
    assert self.c.group.info()["name"] == start


@Xephyr(False, TestConfig())
def test_togglegroup(self):
    self.c.group["a"].toscreen()
    self.c.group["b"].toscreen()
    self.c.screen.togglegroup("c")
    assert self.c.group.info()["name"] == "c"
    self.c.screen.togglegroup("c")
    assert self.c.group.info()["name"] == "b"
    self.c.screen.togglegroup()
    assert self.c.group.info()["name"] == "c"


@Xephyr(False, TestConfig())
def test_inspect_xeyes(self):
    self.testXeyes()
    assert self.c.window.inspect()


@Xephyr(False, TestConfig())
def test_inspect_xterm(self):
    self.testXterm()
    assert self.c.window.inspect()["wm_class"]


@Xephyr(False, TestConfig())
def test_static(self):
    self.testXeyes()
    self.testWindow("one")
    self.c.window[self.c.window.info()["id"]].static(0, 0, 0, 100, 100)


@Xephyr(False, TestConfig())
def test_match(self):
    self.testXeyes()
    assert self.c.window.match(wname="xeyes")
    assert not self.c.window.match(wname="nonexistent")


@Xephyr(False, TestConfig())
def test_default_float(self):
    # change to 2 col stack
    self.c.nextlayout()
    assert len(self.c.layout.info()["stacks"]) == 2
    self.testXclock()

    assert self.c.group.info()['focus'] == 'xclock'
    assert self.c.window.info()['width'] == 164
    assert self.c.window.info()['height'] == 164
    assert self.c.window.info()['x'] == 0
    assert self.c.window.info()['y'] == 0
    assert self.c.window.info()['floating'] == True

    self.c.window.move_floating(10, 20, 42, 42)
    assert self.c.window.info()['width'] == 164
    assert self.c.window.info()['height'] == 164
    assert self.c.window.info()['x'] == 10
    assert self.c.window.info()['y'] == 20
    assert self.c.window.info()['floating'] == True


@Xephyr(False, TestConfig())
def test_last_float_size(self):
    """
    When you re-float something it would be preferable to have it
    use the previous float size
    """
    self.testXeyes()
    assert self.c.window.info()['name'] == 'xeyes'
    assert self.c.window.info()['width'] == 798
    assert self.c.window.info()['height'] == 578
    self.c.window.toggle_floating()
    assert self.c.window.info()['width'] == 150
    assert self.c.window.info()['height'] == 100
    # resize
    self.c.window.set_size_floating(50, 90, 42, 42)
    assert self.c.window.info()['width'] == 50
    assert self.c.window.info()['height'] == 90
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


@Xephyr(False, TestConfig())
def test_float_max_min_combo(self):
    # change to 2 col stack
    self.c.nextlayout()
    assert len(self.c.layout.info()["stacks"]) == 2
    self.testXterm()
    self.testXeyes()

    assert self.c.group.info()['focus'] == 'xeyes'
    assert self.c.window.info()['width'] == 398
    assert self.c.window.info()['height'] == 578
    assert self.c.window.info()['x'] == 400
    assert self.c.window.info()['y'] == 0
    assert self.c.window.info()['floating'] == False

    self.c.window.toggle_maximize()
    assert self.c.window.info()['floating'] == True
    assert self.c.window.info()['maximized'] == True
    assert self.c.window.info()['width'] == 800
    assert self.c.window.info()['height'] == 580
    assert self.c.window.info()['x'] == 0
    assert self.c.window.info()['y'] == 0

    self.c.window.toggle_minimize()
    assert self.c.group.info()['focus'] == 'xeyes'
    assert self.c.window.info()['floating'] == True
    assert self.c.window.info()['minimized'] == True
    assert self.c.window.info()['width'] == 800
    assert self.c.window.info()['height'] == 580
    assert self.c.window.info()['x'] == 0
    assert self.c.window.info()['y'] == 0

    self.c.window.toggle_floating()
    assert self.c.group.info()['focus'] == 'xeyes'
    assert self.c.window.info()['floating'] == False
    assert self.c.window.info()['minimized'] == False
    assert self.c.window.info()['maximized'] == False
    assert self.c.window.info()['width'] == 398
    assert self.c.window.info()['height'] == 578
    assert self.c.window.info()['x'] == 400
    assert self.c.window.info()['y'] == 0


@Xephyr(False, TestConfig())
def test_toggle_fullscreen(self):
    # change to 2 col stack
    self.c.nextlayout()
    assert len(self.c.layout.info()["stacks"]) == 2
    self.testXterm()
    self.testXeyes()

    assert self.c.group.info()['focus'] == 'xeyes'
    assert self.c.window.info()['width'] == 398
    assert self.c.window.info()['height'] == 578
    assert self.c.window.info()['float_info'] == {
        'y': 0, 'x': 400, 'w': 150, 'h': 100}
    assert self.c.window.info()['x'] == 400
    assert self.c.window.info()['y'] == 0

    self.c.window.toggle_fullscreen()
    assert self.c.window.info()['floating'] == True
    assert self.c.window.info()['maximized'] == False
    assert self.c.window.info()['fullscreen'] == True
    assert self.c.window.info()['width'] == 800
    assert self.c.window.info()['height'] == 600
    assert self.c.window.info()['x'] == 0
    assert self.c.window.info()['y'] == 0

    self.c.window.toggle_fullscreen()
    assert self.c.window.info()['floating'] == False
    assert self.c.window.info()['maximized'] == False
    assert self.c.window.info()['fullscreen'] == False
    assert self.c.window.info()['width'] == 398
    assert self.c.window.info()['height'] == 578
    assert self.c.window.info()['x'] == 400
    assert self.c.window.info()['y'] == 0


@Xephyr(False, TestConfig())
def test_toggle_max(self):
    # change to 2 col stack
    self.c.nextlayout()
    assert len(self.c.layout.info()["stacks"]) == 2
    self.testXterm()
    self.testXeyes()

    assert self.c.group.info()['focus'] == 'xeyes'
    assert self.c.window.info()['width'] == 398
    assert self.c.window.info()['height'] == 578
    assert self.c.window.info()['float_info'] == {
        'y': 0, 'x': 400, 'w': 150, 'h': 100}
    assert self.c.window.info()['x'] == 400
    assert self.c.window.info()['y'] == 0

    self.c.window.toggle_maximize()
    assert self.c.window.info()['floating'] == True
    assert self.c.window.info()['maximized'] == True
    assert self.c.window.info()['width'] == 800
    assert self.c.window.info()['height'] == 580
    assert self.c.window.info()['x'] == 0
    assert self.c.window.info()['y'] == 0

    self.c.window.toggle_maximize()
    assert self.c.window.info()['floating'] == False
    assert self.c.window.info()['maximized'] == False
    assert self.c.window.info()['width'] == 398
    assert self.c.window.info()['height'] == 578
    assert self.c.window.info()['x'] == 400
    assert self.c.window.info()['y'] == 0


@Xephyr(False, TestConfig())
def test_toggle_min(self):
    # change to 2 col stack
    self.c.nextlayout()
    assert len(self.c.layout.info()["stacks"]) == 2
    self.testXterm()
    self.testXeyes()

    assert self.c.group.info()['focus'] == 'xeyes'
    assert self.c.window.info()['width'] == 398
    assert self.c.window.info()['height'] == 578
    assert self.c.window.info()['float_info'] == {
        'y': 0, 'x': 400, 'w': 150, 'h': 100}
    assert self.c.window.info()['x'] == 400
    assert self.c.window.info()['y'] == 0

    self.c.window.toggle_minimize()
    assert self.c.group.info()['focus'] == 'xeyes'
    assert self.c.window.info()['floating'] == True
    assert self.c.window.info()['minimized'] == True
    assert self.c.window.info()['width'] == 398
    assert self.c.window.info()['height'] == 578
    assert self.c.window.info()['x'] == 400
    assert self.c.window.info()['y'] == 0

    self.c.window.toggle_minimize()
    assert self.c.group.info()['focus'] == 'xeyes'
    assert self.c.window.info()['floating'] == False
    assert self.c.window.info()['minimized'] == False
    assert self.c.window.info()['width'] == 398
    assert self.c.window.info()['height'] == 578
    assert self.c.window.info()['x'] == 400
    assert self.c.window.info()['y'] == 0


@Xephyr(False, TestConfig())
def test_toggle_floating(self):
    self.testXeyes()
    assert self.c.window.info()['floating'] == False
    self.c.window.toggle_floating()
    assert self.c.window.info()['floating'] == True
    self.c.window.toggle_floating()
    assert self.c.window.info()['floating'] == False
    self.c.window.toggle_floating()
    assert self.c.window.info()['floating'] == True

    #change layout (should still be floating)
    self.c.nextlayout()
    assert self.c.window.info()['floating'] == True


@Xephyr(False, TestConfig())
def test_floating_focus(self):
    # change to 2 col stack
    self.c.nextlayout()
    assert len(self.c.layout.info()["stacks"]) == 2
    self.testXterm()
    self.testXeyes()
    #self.testWindow("one")
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


@Xephyr(False, TestConfig())
def test_move_floating(self):
    self.testXeyes()
    #self.testWindow("one")
    assert self.c.window.info()['width'] == 798
    assert self.c.window.info()['height'] == 578

    assert self.c.window.info()['x'] == 0
    assert self.c.window.info()['y'] == 0
    self.c.window.toggle_floating()
    assert self.c.window.info()['floating'] == True

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

    #change layout (x, y should be same)
    self.c.nextlayout()
    assert self.c.window.info()['width'] == 10
    assert self.c.window.info()['height'] == 20
    assert self.c.window.info()['x'] == 10
    assert self.c.window.info()['y'] == 20


@Xephyr(False, TestConfig(), randr=True)
def test_screens(self):
    assert len(self.c.screens())


@Xephyr(False, TestConfig(), randr=True)
def test_rotate(self):
    self.testWindow("one")
    s = self.c.screens()[0]
    height, width = s["height"], s["width"]
    subprocess.call(
        [
            "xrandr",
            "--output", "default",
            "-display", utils.DISPLAY,
            "--rotate", "left"
        ],
        stderr=subprocess.PIPE,
        stdout=subprocess.PIPE
    )
    s = self.c.screens()[0]
    assert s["height"] == width
    assert s["width"] == height


@Xephyr(False, TestConfig(), randr=True)
def test_resize_(self):
    self.testWindow("one")
    subprocess.call(
        [
            "xrandr",
            "-s", "480x640",
            "-display", utils.DISPLAY
        ]
    )
    d = self.c.screen.info()
    assert d["width"] == 480
    assert d["height"] == 640


# Due to https://github.com/nose-devs/nose/issues/478, nose 1.1.2 ignores
# attributes on yielded functions. Workaround is to attach the attribute
# to the generator function. Can be removed once the issue is resolved.
@attr('xephyr')
def qtile_tests():
    for config in (BareConfig, TestConfig):
        for xinerama in (True, False):
            @Xephyr(xinerama, config)
            def test_xeyes(self):
                self.testXeyes()
            yield test_xeyes

            @Xephyr(xinerama, config)
            def test_xterm(self):
                self.testXterm()
            yield test_xterm

            @Xephyr(xinerama, config)
            def test_xterm_kill(self):
                self.testXterm()
                self.c.window.kill()
                self.c.sync()
                time.sleep(0.1)
                assert not self.c.windows()
            yield test_xterm_kill

            @Xephyr(xinerama, config)
            def test_mapRequest(self):
                self.testWindow("one")
                info = self.c.groups()["a"]
                assert "one" in info["windows"]
                assert info["focus"] == "one"

                self.testWindow("two")
                info = self.c.groups()["a"]
                assert "two" in info["windows"]
                assert info["focus"] == "two"
            yield test_mapRequest

            @Xephyr(xinerama, config)
            def test_unmap(self):
                one = self.testWindow("one")
                two = self.testWindow("two")
                three = self.testWindow("three")
                info = self.c.groups()["a"]
                assert info["focus"] == "three"

                assert len(self.c.windows()) == 3
                self.kill(three)

                assert len(self.c.windows()) == 2
                info = self.c.groups()["a"]
                assert info["focus"] == "two"

                self.kill(two)
                assert len(self.c.windows()) == 1
                info = self.c.groups()["a"]
                assert info["focus"] == "one"

                self.kill(one)
                assert len(self.c.windows()) == 0
                info = self.c.groups()["a"]
                assert info["focus"] == None
            yield test_unmap

            @Xephyr(xinerama, config)
            def test_setgroup(self):
                self.testWindow("one")
                self.c.group["b"].toscreen()
                self._groupconsistency()
                if len(self.c.screens()) == 1:
                    assert self.c.groups()["a"]["screen"] == None
                else:
                    assert self.c.groups()["a"]["screen"] == 1
                assert self.c.groups()["b"]["screen"] == 0
                self.c.group["c"].toscreen()
                self._groupconsistency()
                assert self.c.groups()["c"]["screen"] == 0
            yield test_setgroup

            @Xephyr(xinerama, config)
            def test_unmap_noscreen(self):
                self.testWindow("one")
                pid = self.testWindow("two")
                assert len(self.c.windows()) == 2
                self.c.group["c"].toscreen()
                self._groupconsistency()
                self.c.status()
                assert len(self.c.windows()) == 2
                self.kill(pid)
                assert len(self.c.windows()) == 1
                assert self.c.groups()["a"]["focus"] == "one"
            yield test_unmap_noscreen


def test_init():
    assert_raises(
        libqtile.manager.QtileError,
        libqtile.config.Key,
        [], "unknown", libqtile.command._Call("base", None, "foo")
    )
    assert_raises(
        libqtile.manager.QtileError,
        libqtile.config.Key,
        ["unknown"], "x", libqtile.command._Call("base", None, "foo")
    )


class TScreen(libqtile.config.Screen):
    def setGroup(self, x):
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


class _Config:
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


@Xephyr(False, ClientNewStaticConfig())
def test_minimal_(self):
    a = self.testWindow("one")
    self.kill(a)

if utils.whereis("gkrellm"):
    @Xephyr(False, ClientNewStaticConfig())
    def test_gkrellm(self):
        self.testGkrellm()
        time.sleep(0.1)


class ToGroupConfig(_Config):
    @staticmethod
    def main(c):
        def client_new(c):
            c.togroup("d")
        libqtile.hook.subscribe.client_new(client_new)


@Xephyr(False, ToGroupConfig())
def test_minimal__(self):
    self.c.group["d"].toscreen()
    self.c.group["a"].toscreen()
    a = self.testWindow("one")
    assert len(self.c.group["d"].info()["windows"]) == 1
    self.kill(a)
