import libpry, time, pprint
from libqtile import layout
import utils


class MaxConfig:
    groups = ["a", "b", "c", "d"]
    layouts = [
        layout.Max()
    ]
    keys = []
    screens = []


class uMax(utils.QtileTests):
    config = MaxConfig()
    def test_simple(self):
        self.testWindow("one")
        assert self.c.layout.info() == ["one"]
        self.testWindow("two")
        assert self.c.layout.info() == ["two", "one"]

    def test_updown(self):
        self.testWindow("one")
        self.testWindow("two")
        self.testWindow("three")
        assert self.c.layout.info() == ["three", "two", "one"]
        self.c.layout.down()
        assert self.c.layout.info() == ["two", "one","three"]
        self.c.layout.up()
        assert self.c.layout.info() == ["three", "two", "one"]

    def test_remove(self):
        self.testWindow("one")
        two = self.testWindow("two")
        assert self.c.layout.info() == ["two", "one"]
        self.kill(two)
        assert self.c.layout.info() == ["one"]


class StackConfig:
    groups = ["a", "b", "c", "d"]
    layouts = [
        layout.Stack(stacks=2, borderWidth=10),
        layout.Stack(stacks=1, borderWidth=10),
    ]
    keys = []
    screens = []


class uStack(utils.QtileTests):
    config = StackConfig()
    def _stacks(self):
        stacks = []
        for i in self.c.layout.info()["stacks"]:
            windows = i["windows"]
            current = i["current"]
            stacks.append(windows[current:] + windows[:current])
        return stacks

    def test_stack_commands(self):
        assert self.c.layout.info()["current_stack"] == 0
        self.testWindow("one")
        assert self._stacks() == [["one"], []]
        assert self.c.layout.info()["current_stack"] == 0
        self.testWindow("two")
        assert self._stacks() == [["one"], ["two"]]
        assert self.c.layout.info()["current_stack"] == 1
        self.testWindow("three")
        assert self._stacks() == [["one"], ["three", "two"]]
        assert self.c.layout.info()["current_stack"] == 1

        self.c.layout.delete()
        assert self._stacks() == [["one", "three", "two"]]
        info = self.c.groups()["a"]
        assert info["focus"] == "one"
        self.c.layout.delete()
        assert len(self._stacks()) == 1

        self.c.layout.add()
        assert self._stacks() == [["one", "three", "two"], []]

        self.c.layout.rotate()
        assert self._stacks() == [[], ["one", "three", "two"]]

    def test_cmd_down(self):
        self.c.layout.down()

    def test_addremove(self):
        one = self.testWindow("one")
        self.c.layout.next()
        two = self.testWindow("two")
        three = self.testWindow("three")
        assert self._stacks() == [['one'], ['three', 'two']]
        assert self.c.layout.info()["current_stack"] == 1
        self.kill(three)
        assert self.c.layout.info()["current_stack"] == 1
        self.kill(two)
        assert self.c.layout.info()["current_stack"] == 0
        self.c.layout.next()
        two = self.testWindow("two")
        self.c.layout.next()
        assert self.c.layout.info()["current_stack"] == 0
        self.kill(one)
        assert self.c.layout.info()["current_stack"] == 1

    def test_rotation(self):
        self.c.layout.delete()
        self.testWindow("one")
        self.testWindow("two")
        self.testWindow("three")
        assert self._stacks() == [["three", "two", "one"]]
        self.c.layout.down()
        assert self._stacks() == [["one", "three", "two"]]
        self.c.layout.up()
        assert self._stacks() == [["three", "two", "one"]]
        self.c.layout.down()
        self.c.layout.down()
        assert self._stacks() == [["two", "one", "three"]]
        
    def test_nextprev(self):
        self.c.layout.add()
        one = self.testWindow("one")
        two = self.testWindow("two")
        three = self.testWindow("three")

        assert self.c.groups()["a"]["focus"] == "three"
        self.c.layout.next()
        assert self.c.groups()["a"]["focus"] == "one"

        self.c.layout.previous()
        assert self.c.groups()["a"]["focus"] == "three"
        self.c.layout.previous()
        assert self.c.groups()["a"]["focus"] == "two"

        self.c.layout.next()
        self.c.layout.next()
        self.c.layout.next()
        assert self.c.groups()["a"]["focus"] == "two"

        self.kill(three)
        self.c.layout.next()
        assert self.c.groups()["a"]["focus"] == "one"
        self.c.layout.previous()
        assert self.c.groups()["a"]["focus"] == "two"
        self.c.layout.next()
        self.kill(two)
        self.c.layout.next()
        assert self.c.groups()["a"]["focus"] == "one"

        self.kill(one)
        self.c.layout.next()
        assert self.c.groups()["a"]["focus"] == None
        self.c.layout.previous()
        assert self.c.groups()["a"]["focus"] == None

    def test_window_removal(self):
        self.c.layout.next()
        one = self.testWindow("one")
        two = self.testWindow("two")
        self.c.layout.down()
        self.kill(two)

    def test_split(self):
        one = self.testWindow("one")
        two = self.testWindow("two")
        three = self.testWindow("three")
        stacks = self.c.layout.info()["stacks"]
        assert not stacks[1]["split"]
        self.c.layout.toggle_split()
        stacks = self.c.layout.info()["stacks"]
        assert stacks[1]["split"]

    def test_shuffle(self):
        self.c.nextlayout()
        one = self.testWindow("one")
        two = self.testWindow("two")
        three = self.testWindow("three")

        stack = self.c.layout.info()["stacks"][0]
        assert stack["windows"][stack["current"]] == "three"
        for i in range(5):
            self.c.layout.shuffle_up()
            stack = self.c.layout.info()["stacks"][0]
            assert stack["windows"][stack["current"]] == "three"
        for i in range(5):
            self.c.layout.shuffle_down()
            stack = self.c.layout.info()["stacks"][0]
            assert stack["windows"][stack["current"]] == "three"

    def test_client_to(self):
        one = self.testWindow("one")
        two = self.testWindow("two")
        assert self.c.layout.info()["stacks"][0]["windows"] == ["one"]
        self.c.layout.client_to_previous()
        assert self.c.layout.info()["stacks"][0]["windows"] == ["two", "one"]
        self.c.layout.client_to_previous()
        assert self.c.layout.info()["stacks"][0]["windows"] == ["one"]
        assert self.c.layout.info()["stacks"][1]["windows"] == ["two"]
        self.c.layout.client_to_next()
        assert self.c.layout.info()["stacks"][0]["windows"] == ["two", "one"]

    def test_info(self):
        one = self.testWindow("one")
        assert self.c.layout.info()["stacks"]


class SelectorConfig:
    groups = ["a", "b", "c"]
    layouts = [
        layout.Max(),
        layout.Stack()
    ]
    keys = []
    screens = []


class uSelectors(utils.QtileTests):
    config = StackConfig()
    def test_simple(self):
        pass


tests = [
    utils.xfactory(xinerama=False), [
        uMax(),
        uStack(),
        uSelectors(),
    ],
]
