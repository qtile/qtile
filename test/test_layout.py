import libpry, time, pprint
import libqtile, libqtile.config
import utils

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
        info = self.c.groups()["a"]
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
        assert self.c.stack_get() == [["one", "three", "two"]]
        self.c.stack_up()
        assert self.c.stack_get() == [["three", "two", "one"]]
        self.c.stack_down()
        self.c.stack_down()
        assert self.c.stack_get() == [["two", "one", "three"]]
        
    def test_nextprev(self):
        self.c.stack_add()
        one = self.testWindow("one")
        two = self.testWindow("two")
        three = self.testWindow("three")

        assert self.c.groups()["a"]["focus"] == "three"
        self.c.stack_next()
        assert self.c.groups()["a"]["focus"] == "one"

        self.c.stack_previous()
        assert self.c.groups()["a"]["focus"] == "three"
        self.c.stack_previous()
        assert self.c.groups()["a"]["focus"] == "two"

        self.c.stack_next()
        self.c.stack_next()
        self.c.stack_next()
        assert self.c.groups()["a"]["focus"] == "two"

        self.kill(three)
        self.c.stack_next()
        assert self.c.groups()["a"]["focus"] == "one"
        self.c.stack_previous()
        assert self.c.groups()["a"]["focus"] == "two"
        self.c.stack_next()
        self.kill(two)
        self.c.stack_next()
        assert self.c.groups()["a"]["focus"] == "one"

        self.kill(one)
        self.c.stack_next()
        assert self.c.groups()["a"]["focus"] == None
        self.c.stack_previous()
        assert self.c.groups()["a"]["focus"] == None

    def test_window_removal(self):
        self.c.nextlayout()
        one = self.testWindow("one")
        two = self.testWindow("two")
        self.c.stack_down()
        self.kill(one)

    def test_split(self):
        one = self.testWindow("one")
        two = self.testWindow("two")
        three = self.testWindow("three")
        stacks = self.c.layoutinfo()["stacks"]
        assert not stacks[1]["split"]
        self.c.stack_toggle_split()
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
            self.c.stack_shuffle_up()
            stack = self.c.layoutinfo()["stacks"][0]
            assert stack["windows"][stack["current"]] == "three"
        for i in range(5):
            self.c.stack_shuffle_down()
            stack = self.c.layoutinfo()["stacks"][0]
            assert stack["windows"][stack["current"]] == "three"

    def test_info(self):
        one = self.testWindow("one")
        assert self.c.layoutinfo()["stacks"]


tests = [
    utils.XNest(xinerama=False), [
        uStack(),
    ],
]
