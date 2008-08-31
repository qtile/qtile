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
    groups = ["a"]
    layouts = [
        libqtile.layout.Stack(stacks=1, borderWidth=10),
        libqtile.layout.Stack(stacks=2, borderWidth=10),
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
        

tests = [
    utils.XNest(xinerama=False), [
        uCall(),
        uDoc()
    ]
]
