# Copyright (c) 2011 Florian Mounier
# Copyright (c) 2012, 2014 Tycho Andersen
# Copyright (c) 2013 Craig Barnes
# Copyright (c) 2014 Sean Vig
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

import libqtile.bar
import libqtile.config
import libqtile.confreader
import libqtile.layout
import libqtile.log_utils
import libqtile.widget
from libqtile.command.base import CommandObject
from libqtile.command.interface import CommandError
from libqtile.confreader import Config
from libqtile.lazy import lazy
from test.conftest import dualmonitor


class CallConfig(Config):
    keys = [
        libqtile.config.Key(
            ["control"],
            "j",
            lazy.layout.down(),
        ),
        libqtile.config.Key(
            ["control"],
            "k",
            lazy.layout.up(),
        ),
    ]
    mouse = []
    groups = [
        libqtile.config.Group("a"),
        libqtile.config.Group("b"),
    ]
    layouts = [
        libqtile.layout.Stack(num_stacks=1),
        libqtile.layout.Max(),
    ]
    floating_layout = libqtile.resources.default_config.floating_layout
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


call_config = pytest.mark.parametrize("manager", [CallConfig], indirect=True)


@call_config
def test_layout_filter(manager):
    manager.test_window("one")
    manager.test_window("two")
    assert manager.c.groups()["a"]["focus"] == "two"
    manager.c.simulate_keypress(["control"], "j")
    assert manager.c.groups()["a"]["focus"] == "one"
    manager.c.simulate_keypress(["control"], "k")
    assert manager.c.groups()["a"]["focus"] == "two"


class TestCommands(CommandObject):
    @staticmethod
    def cmd_one():
        pass

    def cmd_one_self(self):
        pass

    def cmd_two(self, a):
        pass

    def cmd_three(self, a, b=99):
        pass

    def _items(self, name):
        return None

    def _select(self, name, sel):
        return None


def test_doc():
    c = TestCommands()
    assert "one()" in c.cmd_doc("one")
    assert "one_self()" in c.cmd_doc("one_self")
    assert "two(a)" in c.cmd_doc("two")
    assert "three(a, b=99)" in c.cmd_doc("three")


def test_commands():
    c = TestCommands()
    assert len(c.cmd_commands()) == 9


def test_command():
    c = TestCommands()
    assert c.command("one")
    assert not c.command("nonexistent")


class ServerConfig(Config):
    auto_fullscreen = True
    keys = []
    mouse = []
    groups = [
        libqtile.config.Group("a"),
        libqtile.config.Group("b"),
        libqtile.config.Group("c"),
    ]
    layouts = [
        libqtile.layout.Stack(num_stacks=1),
        libqtile.layout.Stack(num_stacks=2),
        libqtile.layout.Stack(num_stacks=3),
    ]
    floating_layout = libqtile.resources.default_config.floating_layout
    screens = [
        libqtile.config.Screen(
            bottom=libqtile.bar.Bar(
                [
                    libqtile.widget.TextBox(name="one"),
                ],
                20,
            ),
        ),
        libqtile.config.Screen(
            bottom=libqtile.bar.Bar(
                [
                    libqtile.widget.TextBox(name="two"),
                ],
                20,
            ),
        ),
    ]


server_config = pytest.mark.parametrize("manager", [ServerConfig], indirect=True)


@server_config
def test_cmd_commands(manager):
    assert manager.c.commands()
    assert manager.c.layout.commands()
    assert manager.c.screen.bar["bottom"].commands()


@server_config
def test_call_unknown(manager):
    with pytest.raises(libqtile.command.client.SelectError, match="Not valid child or command"):
        manager.c.nonexistent

    manager.c.layout
    with pytest.raises(libqtile.command.client.SelectError, match="Not valid child or command"):
        manager.c.layout.nonexistent


@dualmonitor
@server_config
def test_items_qtile(manager):
    v = manager.c.items("group")
    assert v[0]
    assert sorted(v[1]) == ["a", "b", "c"]

    assert manager.c.items("layout") == (True, [0, 1, 2])

    v = manager.c.items("widget")
    assert not v[0]
    assert sorted(v[1]) == ["one", "two"]

    assert manager.c.items("bar") == (False, ["bottom"])
    t, lst = manager.c.items("window")
    assert t
    assert len(lst) == 2
    assert manager.c.window[lst[0]]
    assert manager.c.items("screen") == (True, [0, 1])


@dualmonitor
@server_config
def test_select_qtile(manager):
    assert manager.c.layout.info()["group"] == "a"
    assert len(manager.c.layout.info()["stacks"]) == 1
    assert len(manager.c.layout[2].info()["stacks"]) == 3
    with pytest.raises(libqtile.command.client.SelectError, match="Item not available in object"):
        manager.c.layout[99]

    assert manager.c.group.info()["name"] == "a"
    assert manager.c.group["c"].info()["name"] == "c"
    with pytest.raises(libqtile.command.client.SelectError, match="Item not available in object"):
        manager.c.group["nonexistent"]

    assert manager.c.widget["one"].info()["name"] == "one"
    with pytest.raises(CommandError, match="No object widget"):
        manager.c.widget.info()

    assert manager.c.bar["bottom"].info()["position"] == "bottom"

    manager.test_window("one")
    wid = manager.c.window.info()["id"]
    assert manager.c.window[wid].info()["id"] == wid

    assert manager.c.screen.info()["index"] == 0
    assert manager.c.screen[1].info()["index"] == 1
    with pytest.raises(libqtile.command.client.SelectError, match="Item not available in object"):
        manager.c.screen[22]


@server_config
def test_items_group(manager):
    group = manager.c.group

    manager.test_window("test")
    wid = manager.c.window.info()["id"]

    assert group.items("window") == (True, [wid])
    assert group.items("layout") == (True, [0, 1, 2])
    assert group.items("screen") == (True, [])


@dualmonitor
@server_config
def test_select_group(manager):
    group = manager.c.group

    assert group.layout.info()["group"] == "a"
    assert len(group.layout.info()["stacks"]) == 1
    assert len(group.layout[2].info()["stacks"]) == 3

    with pytest.raises(CommandError):
        manager.c.group.window.info()
    manager.test_window("test")
    wid = manager.c.window.info()["id"]

    assert group.window.info()["id"] == wid
    assert group.window[wid].info()["id"] == wid
    with pytest.raises(libqtile.command.client.SelectError, match="Item not available in object"):
        group.window["foo"]

    assert group.screen.info()["index"] == 0
    assert group["b"].screen.info()["index"] == 1
    with pytest.raises(libqtile.command.client.SelectError, match="Item not available in object"):
        group.screen[0]


@server_config
def test_items_screen(manager):
    s = manager.c.screen
    assert s.items("layout") == (True, [0, 1, 2])

    manager.test_window("test")
    wid = manager.c.window.info()["id"]
    assert s.items("window") == (True, [wid])

    assert s.items("bar") == (False, ["bottom"])


@server_config
def test_select_screen(manager):
    screen = manager.c.screen
    assert screen.layout.info()["group"] == "a"
    assert len(screen.layout.info()["stacks"]) == 1
    assert len(screen.layout[2].info()["stacks"]) == 3

    with pytest.raises(CommandError):
        manager.c.window.info()

    manager.test_window("test")
    wid = manager.c.window.info()["id"]
    assert screen.window.info()["id"] == wid
    assert screen.window[wid].info()["id"] == wid

    with pytest.raises(CommandError, match="No object"):
        screen.bar.info()
    with pytest.raises(libqtile.command.client.SelectError, match="Item not available in object"):
        screen.bar["top"]

    assert screen.bar["bottom"].info()["position"] == "bottom"


@server_config
def test_items_bar(manager):
    assert manager.c.bar["bottom"].items("screen") == (True, [])


@dualmonitor
@server_config
def test_select_bar(manager):
    assert manager.c.screen[1].bar["bottom"].screen.info()["index"] == 1
    b = manager.c.bar
    assert b["bottom"].screen.info()["index"] == 0
    with pytest.raises(CommandError):
        b.screen.info()


@server_config
def test_items_layout(manager):
    assert manager.c.layout.items("screen") == (True, [])
    assert manager.c.layout.items("group") == (True, [])


@server_config
def test_select_layout(manager):
    layout = manager.c.layout

    assert layout.screen.info()["index"] == 0
    with pytest.raises(libqtile.command.client.SelectError, match="Item not available in object"):
        layout.screen[0]

    assert layout.group.info()["name"] == "a"
    with pytest.raises(libqtile.command.client.SelectError, match="Item not available in object"):
        layout.group["a"]


@dualmonitor
@server_config
def test_items_window(manager):
    manager.test_window("test")
    window = manager.c.window
    window.info()["id"]

    assert window.items("group") == (True, [])
    assert window.items("layout") == (True, [0, 1, 2])
    assert window.items("screen") == (True, [])


@dualmonitor
@server_config
def test_select_window(manager):
    manager.test_window("test")
    window = manager.c.window
    window.info()["id"]

    assert window.group.info()["name"] == "a"
    with pytest.raises(libqtile.command.client.SelectError, match="Item not available in object"):
        window.group["a"]

    assert len(window.layout.info()["stacks"]) == 1
    assert len(window.layout[1].info()["stacks"]) == 2

    assert window.screen.info()["index"] == 0
    with pytest.raises(libqtile.command.client.SelectError, match="Item not available in object"):
        window.screen[0]


@server_config
def test_items_widget(manager):
    assert manager.c.widget["one"].items("bar") == (True, [])


@server_config
def test_select_widget(manager):
    widget = manager.c.widget["one"]
    assert widget.bar.info()["position"] == "bottom"
    with pytest.raises(libqtile.command.client.SelectError, match="Item not available in object"):
        widget.bar["bottom"]


def test_core_node(manager, backend_name):
    assert manager.c.core.info()["backend"] == backend_name


def test_lazy_arguments(manager_nospawn):

    # Decorated function to be bound to key presses
    @lazy.function
    def test_func(qtile, value, multiplier=1):
        qtile.test_func_output = value * multiplier

    config = ServerConfig
    config.keys = [
        libqtile.config.Key(
            ["control"],
            "j",
            test_func(10),
        ),
        libqtile.config.Key(["control"], "k", test_func(5, multiplier=100)),
    ]

    manager_nospawn.start(config)

    manager_nospawn.c.simulate_keypress(["control"], "j")
    _, val = manager_nospawn.c.eval("self.test_func_output")
    assert val == "10"

    manager_nospawn.c.simulate_keypress(["control"], "k")
    _, val = manager_nospawn.c.eval("self.test_func_output")
    assert val == "500"


def test_deprecated_modules(caplog):
    libqtile.log_utils.init_log(logging.WARNING, log_path=None, log_color=False)

    from libqtile.command_client import InteractiveCommandClient  # noqa: F401

    assert caplog.record_tuples == [
        (
            "libqtile",
            logging.WARNING,
            "libqtile.command_client is deprecated. It has been moved to libqtile.command.client",
        )
    ]

    caplog.clear()

    from libqtile.command_graph import CommandGraphNode  # noqa: F401

    assert caplog.record_tuples == [
        (
            "libqtile",
            logging.WARNING,
            "libqtile.command_graph is deprecated. It has been moved to libqtile.command.graph",
        )
    ]

    caplog.clear()

    from libqtile.command_interface import CommandInterface  # noqa: F401

    assert caplog.record_tuples == [
        (
            "libqtile",
            logging.WARNING,
            "libqtile.command_interface is deprecated. It has been moved to libqtile.command.interface",
        )
    ]

    caplog.clear()

    from libqtile.command_object import CommandObject  # noqa: F401

    assert caplog.record_tuples == [
        (
            "libqtile",
            logging.WARNING,
            "libqtile.command_object is deprecated. It has been moved to libqtile.command.base.",
        )
    ]
