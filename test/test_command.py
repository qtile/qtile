import libpry
import libqtile
import utils

class CallConfig(libqtile.config.Config):
    keys = [
        libqtile.manager.Key(
            ["control"], "j",
            libqtile.command.Call("stack_down")
        ),
        libqtile.manager.Key(
            ["control"], "k",
            libqtile.command.Call("stack_up"),
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


class TestCommands(libqtile.command.Commands):
    @staticmethod
    def cmd_one(q): pass
    def cmd_one_self(self, q): pass
    def cmd_two(self, q, a): pass
    def cmd_three(self, q, a, b=99): pass


class uDoc(libpry.AutoTree):
    def test_signatures(self):
        c = TestCommands()
        assert "one()" in c.doc("one")
        assert "one_self()" in c.doc("one_self")
        assert "two(a)" in c.doc("two")
        assert "three(a, b=99)" in c.doc("three")
        


class TestCmdRoot(libqtile.command._CommandRoot):
    def call(self, *args):
        return args


class u_CommandTree(libpry.AutoTree):
    def test_simple(self):
        c = TestCmdRoot(CallConfig())
        assert c.layout.stack_next()
        assert c.layout["b"].stack_next()
        assert c.layout["b"].max_up()
        assert c.layout["b"][0].stack_next()
        assert c.layout["b"][1].max_up()
        libpry.raises(AttributeError, getattr, c.layout["b"][1], "stack_next")
        assert c.widget["text"]



tests = [
    utils.XNest(xinerama=False), [
        uCall(),
        uDoc(),
        u_CommandTree()
    ]
]
