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
    def test_simple(self):
        c = libqtile.command._CommandTree(lambda x: x, "base", [])
        x = c["one"]["two"]
        assert x.selectors == ["one", "two"]
        assert x.klass == "base"
        cmd = x.foo


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
        libpry.raises("unknown command", self.c.nonexistent)
        libpry.raises("unknown command", self.c.layout.nonexistent)

    def test_call_layouts(self):
        assert self.c.layout.info()["group"] == "a"
        assert self.c.layout["a"].info()["group"] == "a"
        assert self.c.layout["b"].info()["group"] == "b"
        assert self.c.layout["c"].info()["group"] == "c"
        libpry.raises("no such group", self.c.layout["nonexistent"].info)
        
        l = self.c.layout["a"][0].info()
        assert len(l["stacks"]) == 1
        assert l["group"] == "a"

        l = self.c.layout["a"][2].info()
        assert len(l["stacks"]) == 3
        assert l["group"] == "a"

        l = self.c.layout["c"][2].info()
        assert len(l["stacks"]) == 3
        assert l["group"] == "c"

        libpry.raises("invalid layout offset", self.c.layout["c"]["foo"].info)
        libpry.raises("invalid layout offset", self.c.layout["c"][22].info)

tests = [
    uCommandObject(),
    utils.XNest(xinerama=True), [
        uCall(),
        u_Server(),
    ],
    u_CommandTree(),
]
