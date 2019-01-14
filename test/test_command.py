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

import pytest

import libqtile
import libqtile.confreader
import libqtile.manager
import libqtile.config
import libqtile.layout
import libqtile.bar
import libqtile.widget


class CallConfig:
    keys = [
        libqtile.config.Key(
            ["control"], "j",
            libqtile.command._Call([("layout", None)], "down")
        ),
        libqtile.config.Key(
            ["control"], "k",
            libqtile.command._Call([("layout", None)], "up"),
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
    floating_layout = libqtile.layout.floating.Floating()
    screens = [
        libqtile.config.Screen(
            bottom=libqtile.bar.Bar(
                [
                    libqtile.widget.GroupBox(),
                ],
                20
            ),
        )
    ]
    main = None
    auto_fullscreen = True


call_config = pytest.mark.parametrize("qtile", [CallConfig], indirect=True)


@call_config
def test_layout_filter(qtile):
    qtile.test_window("one")
    qtile.test_window("two")
    assert qtile.c.groups()["a"]["focus"] == "two"
    qtile.c.simulate_keypress(["control"], "j")
    assert qtile.c.groups()["a"]["focus"] == "one"
    qtile.c.simulate_keypress(["control"], "k")
    assert qtile.c.groups()["a"]["focus"] == "two"


class TestCommands(libqtile.command.CommandObject):
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


class ConcreteCmdRoot(libqtile.command._CommandRoot):
    def call(self, *args):
        return args

    def _items(self, name):
        return None

    def _select(self, name, sel):
        return None


def test_selectors():
    c = ConcreteCmdRoot()

    s = c.layout.screen.info
    assert s.selectors == [('layout', None), ('screen', None)]

    assert isinstance(c.info, libqtile.command._Command)

    g = c.group
    assert isinstance(g, libqtile.command._TGroup)
    assert g.myselector is None

    g = c.group["one"]
    assert isinstance(g, libqtile.command._TGroup)
    assert g.myselector == "one"

    cmd = c.group["one"].foo
    assert cmd.name == "foo"
    assert cmd.selectors == [('group', 'one')]

    g = c.group["two"].layout["three"].screen
    assert g.selectors == [('group', 'two'), ('layout', 'three')]

    g = c.one
    assert g.selectors == []


class ServerConfig:
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
    floating_layout = libqtile.layout.floating.Floating()
    screens = [
        libqtile.config.Screen(
            bottom=libqtile.bar.Bar(
                [
                    libqtile.widget.TextBox(name="one"),
                ],
                20
            ),
        ),
        libqtile.config.Screen(
            bottom=libqtile.bar.Bar(
                [
                    libqtile.widget.TextBox(name="two"),
                ],
                20
            ),
        )
    ]
    main = None


server_config = pytest.mark.parametrize("qtile", [ServerConfig], indirect=True)


@server_config
def test_cmd_commands(qtile):
    assert qtile.c.commands()
    assert qtile.c.layout.commands()
    assert qtile.c.screen.bar["bottom"].commands()


@server_config
def test_call_unknown(qtile):
    with pytest.raises(libqtile.command.CommandError):
        qtile.c.nonexistent()

    with pytest.raises(libqtile.command.CommandError):
        qtile.c.layout.nonexistent()


@server_config
def test_items_qtile(qtile):
    v = qtile.c.items("group")
    assert v[0]
    assert sorted(v[1]) == ["a", "b", "c"]

    assert qtile.c.items("layout") == (True, [0, 1, 2])

    v = qtile.c.items("widget")
    assert not v[0]
    assert sorted(v[1]) == ['one', 'two']

    assert qtile.c.items("bar") == (False, ["bottom"])
    t, lst = qtile.c.items("window")
    assert t
    assert len(lst) == 2
    assert qtile.c.window[lst[0]]
    assert qtile.c.items("screen") == (True, [0, 1])


@server_config
def test_select_qtile(qtile):
    assert qtile.c.foo.selectors == []
    assert qtile.c.layout.info()["group"] == "a"
    assert len(qtile.c.layout.info()["stacks"]) == 1
    assert len(qtile.c.layout[2].info()["stacks"]) == 3
    with pytest.raises(libqtile.command.CommandError):
        qtile.c.layout[99].info()

    assert qtile.c.group.info()["name"] == "a"
    assert qtile.c.group["c"].info()["name"] == "c"
    with pytest.raises(libqtile.command.CommandError):
        qtile.c.group["nonexistent"].info()

    assert qtile.c.widget["one"].info()["name"] == "one"
    with pytest.raises(libqtile.command.CommandError):
        qtile.c.widget.info()

    assert qtile.c.bar["bottom"].info()["position"] == "bottom"

    qtile.test_window("one")
    wid = qtile.c.window.info()["id"]
    assert qtile.c.window[wid].info()["id"] == wid

    assert qtile.c.screen.info()["index"] == 0
    assert qtile.c.screen[1].info()["index"] == 1
    with pytest.raises(libqtile.command.CommandError):
        qtile.c.screen[22].info()
    with pytest.raises(libqtile.command.CommandError):
        qtile.c.screen["foo"].info()


@server_config
def test_items_group(qtile):
    g = qtile.c.group
    assert g.items("layout") == (True, [0, 1, 2])

    qtile.test_window("test")
    wid = qtile.c.window.info()["id"]
    assert g.items("window") == (True, [wid])

    assert g.items("screen") == (True, None)


@server_config
def test_select_group(qtile):
    g = qtile.c.group
    assert g.layout.info()["group"] == "a"
    assert len(g.layout.info()["stacks"]) == 1
    assert len(g.layout[2].info()["stacks"]) == 3

    with pytest.raises(libqtile.command.CommandError):
        qtile.c.group.window.info()
    qtile.test_window("test")
    wid = qtile.c.window.info()["id"]

    assert g.window.info()["id"] == wid
    assert g.window[wid].info()["id"] == wid
    with pytest.raises(libqtile.command.CommandError):
        g.window["foo"].info()

    assert g.screen.info()["index"] == 0
    assert g["b"].screen.info()["index"] == 1
    with pytest.raises(libqtile.command.CommandError):
        g["b"].screen[0].info()


@server_config
def test_items_screen(qtile):
    s = qtile.c.screen
    assert s.items("layout") == (True, [0, 1, 2])

    qtile.test_window("test")
    wid = qtile.c.window.info()["id"]
    assert s.items("window") == (True, [wid])

    assert s.items("bar") == (False, ["bottom"])


@server_config
def test_select_screen(qtile):
    s = qtile.c.screen
    assert s.layout.info()["group"] == "a"
    assert len(s.layout.info()["stacks"]) == 1
    assert len(s.layout[2].info()["stacks"]) == 3

    with pytest.raises(libqtile.command.CommandError):
        qtile.c.window.info()
    with pytest.raises(libqtile.command.CommandError):
        qtile.c.window[2].info()
    qtile.test_window("test")
    wid = qtile.c.window.info()["id"]
    assert s.window.info()["id"] == wid
    assert s.window[wid].info()["id"] == wid

    with pytest.raises(libqtile.command.CommandError):
        s.bar.info()
    with pytest.raises(libqtile.command.CommandError):
        s.bar["top"].info()
    assert s.bar["bottom"].info()["position"] == "bottom"


@server_config
def test_items_bar(qtile):
    assert qtile.c.bar["bottom"].items("screen") == (True, None)


@server_config
def test_select_bar(qtile):
    assert qtile.c.screen[1].bar["bottom"].screen.info()["index"] == 1
    b = qtile.c.bar
    assert b["bottom"].screen.info()["index"] == 0
    with pytest.raises(libqtile.command.CommandError):
        b.screen.info()


@server_config
def test_items_layout(qtile):
    assert qtile.c.layout.items("screen") == (True, None)
    assert qtile.c.layout.items("group") == (True, None)


@server_config
def test_select_layout(qtile):
    assert qtile.c.layout.screen.info()["index"] == 0
    with pytest.raises(libqtile.command.CommandError):
        qtile.c.layout.screen[0].info()

    assert qtile.c.layout.group.info()["name"] == "a"
    with pytest.raises(libqtile.command.CommandError):
        qtile.c.layout.group["a"].info()


@server_config
def test_items_window(qtile):
    qtile.test_window("test")
    qtile.c.window.info()["id"]

    assert qtile.c.window.items("group") == (True, None)
    assert qtile.c.window.items("layout") == (True, [0, 1, 2])
    assert qtile.c.window.items("screen") == (True, None)


@server_config
def test_select_window(qtile):
    qtile.test_window("test")
    qtile.c.window.info()["id"]

    assert qtile.c.window.group.info()["name"] == "a"
    with pytest.raises(libqtile.command.CommandError):
        qtile.c.window.group["a"].info()

    assert len(qtile.c.window.layout.info()["stacks"]) == 1
    assert len(qtile.c.window.layout[1].info()["stacks"]) == 2

    assert qtile.c.window.screen.info()["index"] == 0
    with pytest.raises(libqtile.command.CommandError):
        qtile.c.window.screen[0].info()


@server_config
def test_items_widget(qtile):
    assert qtile.c.widget["one"].items("bar") == (True, None)


@server_config
def test_select_widget(qtile):
    w = qtile.c.widget["one"]
    assert w.bar.info()["position"] == "bottom"
    with pytest.raises(libqtile.command.CommandError):
        w.bar["bottom"].info()
