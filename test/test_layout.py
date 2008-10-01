import libpry, time, pprint
import libqtile, libqtile.config
import utils


class MaxConfig(libqtile.config.Config):
    groups = ["a", "b", "c", "d"]
    layouts = [
        libqtile.layout.Max()
    ]
    keys = []
    screens = []


class uMax(utils.QTileTests):
    config = MaxConfig()
    def test_simple(self):
        self.testWindow("one")
        assert self.c.layout.max_get() == ["one"]
        self.testWindow("two")
        assert self.c.layout.max_get() == ["two", "one"]

    def test_updown(self):
        self.testWindow("one")
        self.testWindow("two")
        self.testWindow("three")
        assert self.c.layout.max_get() == ["three", "two", "one"]
        self.c.layout.max_down()
        assert self.c.layout.max_get() == ["two", "one","three"]
        self.c.layout.max_up()
        assert self.c.layout.max_get() == ["three", "two", "one"]

    def test_remove(self):
        self.testWindow("one")
        two = self.testWindow("two")
        assert self.c.layout.max_get() == ["two", "one"]
        self.kill(two)
        assert self.c.layout.max_get() == ["one"]


class StackConfig(libqtile.config.Config):
    groups = ["a", "b", "c", "d"]
    layouts = [
        libqtile.layout.Stack(stacks=2, borderWidth=10),
        libqtile.layout.Stack(stacks=1, borderWidth=10),
    ]
    keys = []
    screens = []


class uStack(utils.QTileTests):
    config = StackConfig()
    def test_stack_commands(self):
        assert self.c.layout.stack_current() == None
        self.testWindow("one")
        assert self.c.layout.stack_get() == [["one"], []]
        assert self.c.layout.stack_current() == 0
        self.testWindow("two")
        assert self.c.layout.stack_get() == [["one"], ["two"]]
        assert self.c.layout.stack_current() == 1
        self.testWindow("three")
        assert self.c.layout.stack_get() == [["one"], ["three", "two"]]
        assert self.c.layout.stack_current() == 1

        self.c.layout.stack_delete()
        assert self.c.layout.stack_get() == [["one", "three", "two"]]
        info = self.c.layout.groups()["a"]
        assert info["focus"] == "one"
        self.c.layout.stack_delete()
        assert len(self.c.layout.stack_get()) == 1

        self.c.layout.stack_add()
        assert self.c.layout.stack_get() == [["one", "three", "two"], []]

        self.c.layout.stack_rotate()
        assert self.c.layout.stack_get() == [[], ["one", "three", "two"]]

    def test_rotation(self):
        self.c.layout.stack_delete()
        self.testWindow("one")
        self.testWindow("two")
        self.testWindow("three")
        assert self.c.layout.stack_get() == [["three", "two", "one"]]
        self.c.layout.stack_down()
        assert self.c.layout.stack_get() == [["one", "three", "two"]]
        self.c.layout.stack_up()
        assert self.c.layout.stack_get() == [["three", "two", "one"]]
        self.c.layout.stack_down()
        self.c.layout.stack_down()
        assert self.c.layout.stack_get() == [["two", "one", "three"]]
        
    def test_nextprev(self):
        self.c.layout.stack_add()
        one = self.testWindow("one")
        two = self.testWindow("two")
        three = self.testWindow("three")

        assert self.c.layout.groups()["a"]["focus"] == "three"
        self.c.layout.stack_next()
        assert self.c.layout.groups()["a"]["focus"] == "one"

        self.c.layout.stack_previous()
        assert self.c.layout.groups()["a"]["focus"] == "three"
        self.c.layout.stack_previous()
        assert self.c.layout.groups()["a"]["focus"] == "two"

        self.c.layout.stack_next()
        self.c.layout.stack_next()
        self.c.layout.stack_next()
        assert self.c.layout.groups()["a"]["focus"] == "two"

        self.kill(three)
        self.c.layout.stack_next()
        assert self.c.layout.groups()["a"]["focus"] == "one"
        self.c.layout.stack_previous()
        assert self.c.layout.groups()["a"]["focus"] == "two"
        self.c.layout.stack_next()
        self.kill(two)
        self.c.layout.stack_next()
        assert self.c.layout.groups()["a"]["focus"] == "one"

        self.kill(one)
        self.c.layout.stack_next()
        assert self.c.layout.groups()["a"]["focus"] == None
        self.c.layout.stack_previous()
        assert self.c.layout.groups()["a"]["focus"] == None

    def test_window_removal(self):
        self.c.nextlayout()
        one = self.testWindow("one")
        two = self.testWindow("two")
        self.c.layout.stack_down()
        self.kill(one)

    def test_split(self):
        one = self.testWindow("one")
        two = self.testWindow("two")
        three = self.testWindow("three")
        stacks = self.c.layoutinfo()["stacks"]
        assert not stacks[1]["split"]
        self.c.layout.stack_toggle_split()
        stacks = self.c.layoutinfo()["stacks"]
        assert stacks[1]["split"]

    def test_shuffle(self):
        self.c.nextlayout()
        one = self.testWindow("one")
        two = self.testWindow("two")
        three = self.testWindow("three")

        stack = self.c.layoutinfo()["stacks"][0]
        assert stack["windows"][stack["current"]] == "three"
        for i in range(5):
            self.c.layout.stack_shuffle_up()
            stack = self.c.layoutinfo()["stacks"][0]
            assert stack["windows"][stack["current"]] == "three"
        for i in range(5):
            self.c.layout.stack_shuffle_down()
            stack = self.c.layoutinfo()["stacks"][0]
            assert stack["windows"][stack["current"]] == "three"

    def test_info(self):
        one = self.testWindow("one")
        assert self.c.layoutinfo()["stacks"]


class SelectorConfig(libqtile.config.Config):
    groups = ["a", "b", "c"]
    layouts = [
        libqtile.layout.Max(),
        libqtile.layout.Stack()
    ]
    keys = []
    screens = []


class uSelectors(utils.QTileTests):
    config = StackConfig()
    def test_simple(self):
        pass


tests = [
    utils.XNest(xinerama=False), [
        uMax(),
        uStack(),
        uSelectors(),
    ],
]
