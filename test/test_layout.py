import libpry
import libqtile, libqtile.config
import utils

class MaxConfig(libqtile.config.Config):
    groups = ["a", "b", "c", "d"]
    layouts = [libqtile.Max()]
    keys = [
        libqtile.Key(["control"], "k", libqtile.Command("max_next")),
        libqtile.Key(["control"], "j", libqtile.Command("max_previous")),
    ]
    screens = []


class StackConfig(libqtile.config.Config):
    groups = ["a", "b", "c", "d"]
    layouts = [libqtile.Stack()]
    keys = [
        #libqtile.Key(["control"], "k", libqtile.Command("max_next")),
        #libqtile.Key(["control"], "j", libqtile.Command("max_previous")),
    ]
    screens = []


class uMax(utils.QTileTests):
    config = MaxConfig()
    def test_max_commands(self):
        self.testWindow("one")
        self.testWindow("two")
        self.testWindow("three")

        info = self.c.groupinfo("a")
        assert info["focus"] == "three"
        self.c.max_next()
        info = self.c.groupinfo("a")
        assert info["focus"] == "two"
        self.c.max_next()
        info = self.c.groupinfo("a")
        assert info["focus"] == "one"
        self.c.max_next()
        info = self.c.groupinfo("a")
        assert info["focus"] == "three"
        self.c.max_previous()
        info = self.c.groupinfo("a")
        assert info["focus"] == "one"


class uStack(utils.QTileTests):
    config = StackConfig()
    def test_stack_commands(self):
        self.testWindow("one")
        assert self.c.stack_get() == [["one"], []]
        self.testWindow("two")
        assert self.c.stack_get() == [["two", "one"], []]


tests = [
    utils.XNest(xinerama=False), [
        uMax(),
        uStack(),
    ],
]
