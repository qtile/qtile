import time
import libpry
import libqtile
import utils

import libqtile.confreader, libqtile.manager, libqtile.layout, libqtile.bar, libqtile.widget

theme = libqtile.manager.Theme()

class CallConfig(libqtile.confreader.Config):
    keys = [
        libqtile.manager.Key(
            ["control"], "j",
            libqtile.command._Call([("layout", None)], "down")
        ),
        libqtile.manager.Key(
            ["control"], "k",
            libqtile.command._Call([("layout", None)], "up"),
        ),
    ]
    groups = ["a", "b"]
    layouts = [
        libqtile.layout.Stack(stacks=1),
        libqtile.layout.Max(),
    ]
    screens = [
        libqtile.manager.Screen(
            bottom=libqtile.bar.Bar(
                        [
                            libqtile.widget.GroupBox(),
                        ],
                        20
                    ),
        )
    ]


class uCall(utils.QtileTests):
    config = CallConfig()
    # FIXME: failing test disabled. For some reason we don't seem
    # to have a keymap in Xnest or Xephyr 99% of the time.
    def _test_layout_filter(self):
        self.testWindow("one")
        self.testWindow("two")
        assert self.c.groups()["a"]["focus"] == "two"
        self.c.simulate_keypress(["control"], "j")
        assert self.c.groups()["a"]["focus"] == "one"
        self.c.simulate_keypress(["control"], "k")
        assert self.c.groups()["a"]["focus"] == "two"


class TestCommands(libqtile.command.CommandObject):
    @staticmethod
    def cmd_one(): pass
    def cmd_one_self(self): pass
    def cmd_two(self, a): pass
    def cmd_three(self, a, b=99): pass


class uCommandObject(libpry.AutoTree):
    def test_doc(self):
        c = TestCommands()
        assert "one()" in c.doc("one")
        assert "one_self()" in c.doc("one_self")
        assert "two(a)" in c.doc("two")
        assert "three(a, b=99)" in c.doc("three")

    def test_commands(self):
        c = TestCommands()
        assert len(c.commands()) == 7

    def test_command(self):
        c = TestCommands()
        assert c.command("one")
        assert not c.command("nonexistent")


class TestCmdRoot(libqtile.command._CommandRoot):
    def call(self, *args):
        return args


class u_CommandTree(libpry.AutoTree):
    def test_selectors(self):
        c = libqtile.command._CommandRoot()

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


class ServerConfig(libqtile.confreader.Config):
    keys = []
    groups = ["a", "b", "c"]
    layouts = [
        libqtile.layout.Stack(stacks=1),
        libqtile.layout.Stack(stacks=2),
        libqtile.layout.Stack(stacks=3),
    ]
    screens = [
        libqtile.manager.Screen(
            bottom=libqtile.bar.Bar(
                        [
                            libqtile.widget.TextBox("one"),
                        ],
                        20
                    ),
        ),
        libqtile.manager.Screen(
            bottom=libqtile.bar.Bar(
                        [
                            libqtile.widget.TextBox("three"),
                        ],
                        20
                    ),
        )
    ]


class u_Server(utils.QtileTests):
    config = ServerConfig()
    def test_cmd_commands(self):
        assert self.c.commands()
        assert self.c.layout.commands()
        assert self.c.screen.bar["bottom"].commands()

    def test_call_unknown(self):
        libpry.raises("no such command", self.c.nonexistent)
        libpry.raises("no such command", self.c.layout.nonexistent)

    def test_items_qtile(self):
        v = self.c.items("group")
        assert v[0]
        assert sorted(v[1]) == ["a", "b", "c"]

        assert self.c.items("layout") == (True, [0, 1, 2])

        v = self.c.items("widget")
        assert not v[0]
        assert sorted(v[1]) == ['four', 'one', 'three', 'two']

        assert self.c.items("bar") == (False, ["bottom"])
        t, lst = self.c.items("window")
        assert t
        assert len(lst) == 2
        assert self.c.window[lst[0]]
        assert self.c.items("screen") == (True, [0, 1])
        libpry.raises("unknown item class", self.c.items, "wibble")

    def test_select_qtile(self):
        assert self.c.foo.selectors == []
        assert self.c.layout.info()["group"] == "a"
        assert len(self.c.layout.info()["stacks"]) == 1
        assert len(self.c.layout[2].info()["stacks"]) == 3
        libpry.raises("no object", self.c.layout[99].info)

        assert self.c.group.info()["name"] == "a"
        assert self.c.group["c"].info()["name"] == "c"
        libpry.raises("no object", self.c.group["nonexistent"].info)

        assert self.c.widget["one"].info()["name"] == "one"
        libpry.raises("no object", self.c.widget.info)

        assert self.c.bar["bottom"].info()["position"] == "bottom"
        
        win = self.testWindow("one")
        wid = self.c.window.info()["id"]
        assert self.c.window[wid].info()["id"] == wid

        assert self.c.screen.info()["index"] == 0
        assert self.c.screen[1].info()["index"] == 1
        libpry.raises("no object", self.c.screen[22].info)
        libpry.raises("no object", self.c.screen["foo"].info)

    def test_items_group(self):
        g = self.c.group
        assert g.items("layout") == (True, [0, 1, 2])

        win = self.testWindow("test")
        wid = self.c.window.info()["id"]
        assert g.items("window") == (True, [wid])

        assert g.items("screen") == (True, None)

    def test_select_group(self):
        g = self.c.group
        assert g.layout.info()["group"] == "a"
        assert len(g.layout.info()["stacks"]) == 1
        assert len(g.layout[2].info()["stacks"]) == 3

        libpry.raises("no object", self.c.group.window.info)
        win = self.testWindow("test")
        wid = self.c.window.info()["id"]

        assert g.window.info()["id"] == wid
        assert g.window[wid].info()["id"] == wid
        libpry.raises("no object", g.window["foo"].info)

        assert g.screen.info()["index"] == 0
        assert g["b"].screen.info()["index"] == 1
        libpry.raises("no object", g["b"].screen[0].info)

    def test_items_screen(self):
        s = self.c.screen
        assert s.items("layout") == (True, [0, 1, 2])

        win = self.testWindow("test")
        wid = self.c.window.info()["id"]
        assert s.items("window") == (True, [wid])

        assert s.items("bar") == (False, ["bottom"])

    def test_select_screen(self):
        s = self.c.screen
        assert s.layout.info()["group"] == "a"
        assert len(s.layout.info()["stacks"]) == 1
        assert len(s.layout[2].info()["stacks"]) == 3

        libpry.raises("no object", self.c.window.info)
        libpry.raises("no object", self.c.window[2].info)
        win = self.testWindow("test")
        wid = self.c.window.info()["id"]
        assert s.window.info()["id"] == wid
        assert s.window[wid].info()["id"] == wid

        libpry.raises("no object", s.bar.info)
        libpry.raises("no object", s.bar["top"].info)
        assert s.bar["bottom"].info()["position"] == "bottom"

    def test_items_bar(self):
        assert self.c.bar["bottom"].items("screen") == (True, None)

    def test_select_bar(self):
        assert self.c.screen[1].bar["bottom"].screen.info()["index"] == 1
        b = self.c.bar
        assert b["bottom"].screen.info()["index"] == 0
        libpry.raises("no object", b.screen.info)

    def test_items_layout(self):
        assert self.c.layout.items("screen") == (True, None)
        assert self.c.layout.items("group") == (True, None)

    def test_select_layout(self):
        assert self.c.layout.screen.info()["index"] == 0
        libpry.raises("no object", self.c.layout.screen[0].info)

        assert self.c.layout.group.info()["name"] == "a"
        libpry.raises("no object", self.c.layout.group["a"].info)

    def test_items_window(self):
        win = self.testWindow("test")
        wid = self.c.window.info()["id"]

        assert self.c.window.items("group") == (True, None)
        assert self.c.window.items("layout") == (True, [0, 1, 2])
        assert self.c.window.items("screen") == (True, None)

    def test_select_window(self):
        win = self.testWindow("test")
        wid = self.c.window.info()["id"]

        assert self.c.window.group.info()["name"] == "a"
        libpry.raises("no object", self.c.window.group["a"].info)

        assert len(self.c.window.layout.info()["stacks"]) == 1
        assert len(self.c.window.layout[1].info()["stacks"]) == 2

        assert self.c.window.screen.info()["index"] == 0
        libpry.raises("no object", self.c.window.screen[0].info)

    def test_items_widget(self):
        assert self.c.widget["one"].items("bar") == (True, None)

    def test_select_widget(self):
        w = self.c.widget["one"]
        assert w.bar.info()["position"] == "bottom"
        libpry.raises("no object", w.bar["bottom"].info)

    
tests = [
    uCommandObject(),
    utils.xfactory(xinerama=True), [
        uCall(),
        u_Server(),
    ],
    u_CommandTree(),
]
