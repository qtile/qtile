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

import libqtile
import libqtile.confreader
import libqtile.manager
import libqtile.config
import libqtile.layout
import libqtile.bar
import libqtile.widget
from .utils import Xephyr
from nose.tools import assert_raises


class CallConfig(object):
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


@Xephyr(True, CallConfig())
def test_layout_filter(self):
    self.testWindow("one")
    self.testWindow("two")
    assert self.c.groups()["a"]["focus"] == "two"
    self.c.simulate_keypress(["control"], "j")
    assert self.c.groups()["a"]["focus"] == "one"
    self.c.simulate_keypress(["control"], "k")
    assert self.c.groups()["a"]["focus"] == "two"


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
    assert "one()" in c.doc("one")
    assert "one_self()" in c.doc("one_self")
    assert "two(a)" in c.doc("two")
    assert "three(a, b=99)" in c.doc("three")


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
    assert g.myselector == None

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


class ServerConfig(object):
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


@Xephyr(True, ServerConfig())
def test_cmd_commands(self):
    assert self.c.commands()
    assert self.c.layout.commands()
    assert self.c.screen.bar["bottom"].commands()


@Xephyr(True, ServerConfig())
def test_call_unknown(self):
    assert_raises(libqtile.command.CommandError, self.c.nonexistent)
    assert_raises(libqtile.command.CommandError, self.c.layout.nonexistent)


@Xephyr(True, ServerConfig())
def test_items_qtile(self):
    v = self.c.items("group")
    assert v[0]
    assert sorted(v[1]) == ["a", "b", "c"]

    assert self.c.items("layout") == (True, [0, 1, 2])

    v = self.c.items("widget")
    assert not v[0]
    assert sorted(v[1]) == ['one', 'two']

    assert self.c.items("bar") == (False, ["bottom"])
    t, lst = self.c.items("window")
    assert t
    assert len(lst) == 2
    assert self.c.window[lst[0]]
    assert self.c.items("screen") == (True, [0, 1])


@Xephyr(True, ServerConfig())
def test_select_qtile(self):
    assert self.c.foo.selectors == []
    assert self.c.layout.info()["group"] == "a"
    assert len(self.c.layout.info()["stacks"]) == 1
    assert len(self.c.layout[2].info()["stacks"]) == 3
    assert_raises(libqtile.command.CommandError, self.c.layout[99].info)

    assert self.c.group.info()["name"] == "a"
    assert self.c.group["c"].info()["name"] == "c"
    assert_raises(
        libqtile.command.CommandError, self.c.group["nonexistent"].info)

    assert self.c.widget["one"].info()["name"] == "one"
    assert_raises(libqtile.command.CommandError, self.c.widget.info)

    assert self.c.bar["bottom"].info()["position"] == "bottom"

    win = self.testWindow("one")
    wid = self.c.window.info()["id"]
    assert self.c.window[wid].info()["id"] == wid

    assert self.c.screen.info()["index"] == 0
    assert self.c.screen[1].info()["index"] == 1
    assert_raises(libqtile.command.CommandError, self.c.screen[22].info)
    assert_raises(libqtile.command.CommandError, self.c.screen["foo"].info)


@Xephyr(True, ServerConfig())
def test_items_group(self):
    g = self.c.group
    assert g.items("layout") == (True, [0, 1, 2])

    win = self.testWindow("test")
    wid = self.c.window.info()["id"]
    assert g.items("window") == (True, [wid])

    assert g.items("screen") == (True, None)


@Xephyr(True, ServerConfig())
def test_select_group(self):
    g = self.c.group
    assert g.layout.info()["group"] == "a"
    assert len(g.layout.info()["stacks"]) == 1
    assert len(g.layout[2].info()["stacks"]) == 3

    assert_raises(libqtile.command.CommandError, self.c.group.window.info)
    win = self.testWindow("test")
    wid = self.c.window.info()["id"]

    assert g.window.info()["id"] == wid
    assert g.window[wid].info()["id"] == wid
    assert_raises(libqtile.command.CommandError, g.window["foo"].info)

    assert g.screen.info()["index"] == 0
    assert g["b"].screen.info()["index"] == 1
    assert_raises(libqtile.command.CommandError, g["b"].screen[0].info)


@Xephyr(True, ServerConfig())
def test_items_screen(self):
    s = self.c.screen
    assert s.items("layout") == (True, [0, 1, 2])

    win = self.testWindow("test")
    wid = self.c.window.info()["id"]
    assert s.items("window") == (True, [wid])

    assert s.items("bar") == (False, ["bottom"])


@Xephyr(True, ServerConfig())
def test_select_screen(self):
    s = self.c.screen
    assert s.layout.info()["group"] == "a"
    assert len(s.layout.info()["stacks"]) == 1
    assert len(s.layout[2].info()["stacks"]) == 3

    assert_raises(libqtile.command.CommandError, self.c.window.info)
    assert_raises(libqtile.command.CommandError, self.c.window[2].info)
    win = self.testWindow("test")
    wid = self.c.window.info()["id"]
    assert s.window.info()["id"] == wid
    assert s.window[wid].info()["id"] == wid

    assert_raises(libqtile.command.CommandError, s.bar.info)
    assert_raises(libqtile.command.CommandError, s.bar["top"].info)
    assert s.bar["bottom"].info()["position"] == "bottom"


@Xephyr(True, ServerConfig())
def test_items_bar(self):
    assert self.c.bar["bottom"].items("screen") == (True, None)


@Xephyr(True, ServerConfig())
def test_select_bar(self):
    assert self.c.screen[1].bar["bottom"].screen.info()["index"] == 1
    b = self.c.bar
    assert b["bottom"].screen.info()["index"] == 0
    assert_raises(libqtile.command.CommandError, b.screen.info)


@Xephyr(True, ServerConfig())
def test_items_layout(self):
    assert self.c.layout.items("screen") == (True, None)
    assert self.c.layout.items("group") == (True, None)


@Xephyr(True, ServerConfig())
def test_select_layout(self):
    assert self.c.layout.screen.info()["index"] == 0
    assert_raises(libqtile.command.CommandError, self.c.layout.screen[0].info)

    assert self.c.layout.group.info()["name"] == "a"
    assert_raises(libqtile.command.CommandError, self.c.layout.group["a"].info)


@Xephyr(True, ServerConfig())
def test_items_window(self):
    win = self.testWindow("test")
    wid = self.c.window.info()["id"]

    assert self.c.window.items("group") == (True, None)
    assert self.c.window.items("layout") == (True, [0, 1, 2])
    assert self.c.window.items("screen") == (True, None)


@Xephyr(True, ServerConfig())
def test_select_window(self):
    win = self.testWindow("test")
    wid = self.c.window.info()["id"]

    assert self.c.window.group.info()["name"] == "a"
    assert_raises(libqtile.command.CommandError, self.c.window.group["a"].info)

    assert len(self.c.window.layout.info()["stacks"]) == 1
    assert len(self.c.window.layout[1].info()["stacks"]) == 2

    assert self.c.window.screen.info()["index"] == 0
    assert_raises(libqtile.command.CommandError, self.c.window.screen[0].info)


@Xephyr(True, ServerConfig())
def test_items_widget(self):
    assert self.c.widget["one"].items("bar") == (True, None)


@Xephyr(True, ServerConfig())
def test_select_widget(self):
    w = self.c.widget["one"]
    assert w.bar.info()["position"] == "bottom"
    assert_raises(libqtile.command.CommandError, w.bar["bottom"].info)
