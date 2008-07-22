import libpry
import libqtile
import utils

class CallConfig(libqtile.config.Config):
    keys = [
        libqtile.Key(
            ["control"], "j",
            libqtile.command.Call("max_next").when(layout="stack")
        ),
        libqtile.Key(
            ["control"], "k",
            libqtile.command.Call("max_previous").when(layout="stack"),
            libqtile.command.Call("max_next").when(layout="max")
        ),
    ]
    groups = ["a"]
    layouts = [
        libqtile.layout.Max(),
        libqtile.layout.Stack(),
    ]


class uCall(utils.QTileTests):
    config = CallConfig()
    def test_layout_filter(self):
        self.testWindow("one")
        self.testWindow("two")
        assert self.c.groups()["a"]["focus"] == "two"
        self.c.simulate_keypress(["control"], "j")
        assert self.c.groups()["a"]["focus"] == "two"
        self.c.simulate_keypress(["control"], "k")
        assert self.c.groups()["a"]["focus"] == "one"
        

tests = [
    utils.XNest(xinerama=False), [
        uCall()
    ]
]
