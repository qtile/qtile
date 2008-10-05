import time
import libpry
import libqtile
import utils

class CallConfig(libqtile.config.Config):
    keys = [
        libqtile.manager.Key(
            ["control"], "j",
            libqtile.command._Call("layout", None, "stack_down")
        ),
        libqtile.manager.Key(
            ["control"], "k",
            libqtile.command._Call("layout", None, "stack_up"),
        ),
    ]
    groups = ["a", "b"]
    layouts = [
        libqtile.layout.Stack(stacks=1, borderWidth=10),
        libqtile.layout.Max(),
    ]
    screens = [
        libqtile.manager.Screen(
            bottom=libqtile.bar.Bar(
                        [
                            libqtile.bar.TextBox("text"),
                            libqtile.bar.MeasureBox("measure", width=100),
                        ],
                        20
                    ),
        )
    ]


class uCall(utils.QTileTests):
    config = CallConfig()
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
        assert len(c.commands()) == 4

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


class ServerConfig(libqtile.config.Config):
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
                            libqtile.bar.TextBox("one"),
                            libqtile.bar.MeasureBox("two", width=100),
                        ],
                        20
                    ),
        ),
        libqtile.manager.Screen(
            bottom=libqtile.bar.Bar(
                        [
                            libqtile.bar.TextBox("three"),
                            libqtile.bar.MeasureBox("four", width=100),
                        ],
                        20
                    ),
        )
    ]


class u_Server(utils.QTileTests):
    config = ServerConfig()
    def test_call_unknown(self):
        libpry.raises("no such command", self.c.nonexistent)
        libpry.raises("no such command", self.c.layout.nonexistent)

    def test_select_qtile(self):
        assert self.c.foo.selectors == []
        assert self.c.layout.info()["group"] == "a"
        assert len(self.c.layout.info()["stacks"]) == 1
        assert len(self.c.layout[2].info()["stacks"]) == 3
        libpry.raises("no such object", self.c.layout[99].info)

        assert self.c.group.info()["name"] == "a"
        assert self.c.group["c"].info()["name"] == "c"
        libpry.raises("no such object", self.c.group["nonexistent"].info)

        assert self.c.widget["one"].info()["name"] == "one"
        libpry.raises("no such object", self.c.widget.info)

        assert self.c.bar["bottom"].info()["position"] == "bottom"
        
        win = self.testWindow("one")
        wid = self.c.window.info()["id"]
        assert self.c.window[wid].info()["id"] == wid

        assert self.c.screen.info()["offset"] == 0
        assert self.c.screen[1].info()["offset"] == 1
        libpry.raises("no such object", self.c.screen[22].info)
        libpry.raises("no such object", self.c.screen["foo"].info)

    def test_select_group(self):
        g = self.c.group
        assert g.layout.info()["group"] == "a"
        assert len(g.layout.info()["stacks"]) == 1
        assert len(g.layout[2].info()["stacks"]) == 3

        libpry.raises("no such object", self.c.group.window.info)
        win = self.testWindow("test")
        wid = self.c.window.info()["id"]

        assert g.window.info()["id"] == wid
        assert g.window[wid].info()["id"] == wid
        libpry.raises("no such object", g.window["foo"].info)

        assert g.screen.info()["offset"] == 0
        assert g["b"].screen.info()["offset"] == 1
        libpry.raises("no such object", g["b"].screen[0].info)


tests = [
    uCommandObject(),
    utils.XNest(xinerama=True), [
        uCall(),
        u_Server(),
    ],
    u_CommandTree(),
]
