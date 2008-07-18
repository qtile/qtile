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
    keys = []
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
        assert self.c.stack_current() == None
        self.testWindow("one")
        assert self.c.stack_get() == [["one"], []]
        assert self.c.stack_current() == 0
        self.testWindow("two")
        assert self.c.stack_get() == [["one"], ["two"]]
        assert self.c.stack_current() == 1
        self.testWindow("three")
        assert self.c.stack_get() == [["one"], ["three", "two"]]
        assert self.c.stack_current() == 1

        self.c.stack_delete()
        assert self.c.stack_get() == [["one", "three", "two"]]
        info = self.c.groupinfo("a")
        assert info["focus"] == "one"
        self.c.stack_delete()
        assert len(self.c.stack_get()) == 1

        self.c.stack_add()
        assert self.c.stack_get() == [["one", "three", "two"], []]

        self.c.stack_rotate()
        assert self.c.stack_get() == [[], ["one", "three", "two"]]

    def test_rotation(self):
        self.c.stack_delete()
        self.testWindow("one")
        self.testWindow("two")
        self.testWindow("three")
        assert self.c.stack_get() == [["three", "two", "one"]]
        self.c.stack_down()
        assert self.c.stack_get() == [["two", "one", "three"]]
        self.c.stack_up()
        assert self.c.stack_get() == [["three", "two", "one"]]
        self.c.stack_down()
        self.c.stack_down()
        assert self.c.stack_get() == [["one", "three", "two"]]
        
    def test_nextprev(self):
        self.c.stack_add()
        self.testWindow("one")
        self.testWindow("two")
        self.testWindow("three")

        info = self.c.groupinfo("a")
        assert info["focus"] == "three"

        self.c.stack_next()
        info = self.c.groupinfo("a")
        assert info["focus"] == "one"




tests = [
    utils.XNest(xinerama=False), [
        uMax(),
        uStack(),
    ],
]
