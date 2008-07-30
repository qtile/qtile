import libpry
import libqtile
import utils

class CallConfig(libqtile.config.Config):
    keys = [
        libqtile.Key(
            ["control"], "j",
            libqtile.command.Call("stack_down")
        ),
        libqtile.Key(
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
        

tests = [
    utils.XNest(xinerama=False), [
        uCall()
    ]
]
