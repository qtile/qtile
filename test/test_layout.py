from libqtile import layout
import libqtile.manager
from time import sleep
from utils import Xephyr


def assertFocused(self, name):
    """Asserts that window with specified name is currently focused"""
    info = self.c.window.info()
    assert info['name']


def assertDimensions(self, x, y, w, h, win=None):
    """Asserts dimensions of window"""
    if win is None:
        win = self.c.window
    info = win.info()
    assert info['x'] == x, info
    assert info['y'] == y, info
    assert info['width'] == w, info  # why?
    assert info['height'] == h, info


def assertFocusPath(self, *names):
    for i in names:
        self.c.group.next_window()
        assertFocused(self, i)
    # let's check twice for sure
    for i in names:
        self.c.group.next_window()
        assertFocused(self, i)
    # Ok, let's check backwards now
    for i in reversed(names):
        assertFocused(self, i)
        self.c.group.prev_window()
    # and twice for sure
    for i in reversed(names):
        assertFocused(self, i)
        self.c.group.prev_window()


class MaxConfig:
    main = None
    groups = [
        libqtile.manager.Group("a"),
        libqtile.manager.Group("b"),
        libqtile.manager.Group("c"),
        libqtile.manager.Group("d")
    ]
    layouts = [
        layout.Max()
    ]
    floating_layout = libqtile.layout.floating.Floating()
    keys = []
    mouse = []
    screens = []


@Xephyr(False, MaxConfig())
def test_max_simple(self):
    self.testWindow("one")
    assert self.c.layout.info()["clients"] == ["one"]
    self.testWindow("two")
    assert self.c.layout.info()["clients"] == ["two", "one"]


@Xephyr(False, MaxConfig())
def test_max_updown(self):
    self.testWindow("one")
    self.testWindow("two")
    self.testWindow("three")
    assert self.c.layout.info()["clients"] == ["three", "two", "one"]
    self.c.layout.down()
    assert self.c.layout.info()["clients"] == ["two", "one", "three"]
    self.c.layout.up()
    assert self.c.layout.info()["clients"] == ["three", "two", "one"]


@Xephyr(False, MaxConfig())
def test_max_remove(self):
    self.testWindow("one")
    two = self.testWindow("two")
    assert self.c.layout.info()["clients"] == ["two", "one"]
    self.kill(two)
    assert self.c.layout.info()["clients"] == ["one"]


class StackConfig:
    main = None
    groups = [
        libqtile.manager.Group("a"),
        libqtile.manager.Group("b"),
        libqtile.manager.Group("c"),
        libqtile.manager.Group("d")
    ]
    layouts = [
        layout.Stack(stacks=2),
        layout.Stack(stacks=1),
    ]
    floating_layout = libqtile.layout.floating.Floating()
    keys = []
    mouse = []
    screens = []
    follow_mouse_focus = False


def _stacks(self):
    stacks = []
    for i in self.c.layout.info()["stacks"]:
        windows = i["windows"]
        current = i["current"]
        stacks.append(windows[current:] + windows[:current])
    return stacks


@Xephyr(False, StackConfig())
def test_stack_commands(self):
    assert self.c.layout.info()["current_stack"] == 0
    self.testWindow("one")
    assert _stacks(self) == [["one"], []]
    assert self.c.layout.info()["current_stack"] == 0
    self.testWindow("two")
    assert _stacks(self) == [["one"], ["two"]]
    assert self.c.layout.info()["current_stack"] == 1
    self.testWindow("three")
    assert _stacks(self) == [["one"], ["three", "two"]]
    assert self.c.layout.info()["current_stack"] == 1

    self.c.layout.delete()
    assert _stacks(self) == [["one", "three", "two"]]
    info = self.c.groups()["a"]
    assert info["focus"] == "one"
    self.c.layout.delete()
    assert len(_stacks(self)) == 1

    self.c.layout.add()
    assert _stacks(self) == [["one", "three", "two"], []]

    self.c.layout.rotate()
    assert _stacks(self) == [[], ["one", "three", "two"]]


@Xephyr(False, StackConfig())
def test_stack_cmd_down(self):
    self.c.layout.down()


@Xephyr(False, StackConfig())
def test_stack_addremove(self):
    one = self.testWindow("one")
    self.c.layout.next()
    two = self.testWindow("two")
    three = self.testWindow("three")
    assert _stacks(self) == [['one'], ['three', 'two']]
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


@Xephyr(False, StackConfig())
def test_stack_rotation(self):
    self.c.layout.delete()
    self.testWindow("one")
    self.testWindow("two")
    self.testWindow("three")
    assert _stacks(self) == [["three", "two", "one"]]
    self.c.layout.down()
    assert _stacks(self) == [["one", "three", "two"]]
    self.c.layout.up()
    assert _stacks(self) == [["three", "two", "one"]]
    self.c.layout.down()
    self.c.layout.down()
    assert _stacks(self) == [["two", "one", "three"]]


@Xephyr(False, StackConfig())
def test_stack_nextprev(self):
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


@Xephyr(False, StackConfig())
def test_stack_window_removal(self):
    self.c.layout.next()
    one = self.testWindow("one")
    two = self.testWindow("two")
    self.c.layout.down()
    self.kill(two)


@Xephyr(False, StackConfig())
def test_stack_split(self):
    one = self.testWindow("one")
    two = self.testWindow("two")
    three = self.testWindow("three")
    stacks = self.c.layout.info()["stacks"]
    assert not stacks[1]["split"]
    self.c.layout.toggle_split()
    stacks = self.c.layout.info()["stacks"]
    assert stacks[1]["split"]


@Xephyr(False, StackConfig())
def test_stack_shuffle(self):
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


@Xephyr(False, StackConfig())
def test_stack_client_to(self):
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


@Xephyr(False, StackConfig())
def test_stack_info(self):
    one = self.testWindow("one")
    assert self.c.layout.info()["stacks"]


class RatioTileConfig:
    main = None
    groups = [
        libqtile.manager.Group("a"),
        libqtile.manager.Group("b"),
        libqtile.manager.Group("c"),
        libqtile.manager.Group("d")
    ]
    layouts = [
        layout.RatioTile(ratio=.5),
        layout.RatioTile(),
        ]
    floating_layout = libqtile.layout.floating.Floating()
    keys = []
    mouse = []
    screens = []
    follow_mouse_focus = False


@Xephyr(False, RatioTileConfig())
def test_ratiotile_add_windows(self):
    for i in range(12):
        self.testWindow(str(i))
        if i == 0:
            assert self.c.layout.info()['layout_info'] == [
                (0, 0, 800, 600)]
        elif i == 1:
            assert self.c.layout.info()['layout_info'] == [
                (0, 0, 400, 600), (400, 0, 400, 600)]
        elif i == 2:
            assert self.c.layout.info()['layout_info'] == [
                (0, 0, 266, 600), (266, 0, 266, 600), (532, 0, 268, 600)]
        elif i == 3:
            assert self.c.layout.info()['layout_info'] == [
                (0, 0, 200, 600), (200, 0, 200, 600), (400, 0, 200, 600),
                (600, 0, 200, 600)]
        elif i == 4:
            assert self.c.layout.info()['layout_info'] == [
                (0, 0, 160, 600), (160, 0, 160, 600), (320, 0, 160, 600),
                (480, 0, 160, 600), (640, 0, 160, 600)]
        elif i == 5:
            assert self.c.layout.info()['layout_info'] == [
                (0, 0, 133, 600), (133, 0, 133, 600), (266, 0, 133, 600),
                (399, 0, 133, 600), (532, 0, 133, 600), (665, 0, 135, 600)]
        elif i == 6:
            assert self.c.layout.info()['layout_info'] == [
                (0, 0, 200, 300), (200, 0, 200, 300), (400, 0, 200, 300),
                (600, 0, 200, 300), (0, 300, 266, 300),
                (266, 300, 266, 300), (532, 300, 268, 300)]
        elif i == 7:
            assert self.c.layout.info()['layout_info'] == [
                (0, 0, 200, 300), (200, 0, 200, 300), (400, 0, 200, 300),
                (600, 0, 200, 300), (0, 300, 200, 300),
                (200, 300, 200, 300), (400, 300, 200, 300),
                (600, 300, 200, 300)]
        elif i == 8:
            assert self.c.layout.info()['layout_info'] == [
                (0, 0, 160, 300), (160, 0, 160, 300), (320, 0, 160, 300),
                (480, 0, 160, 300), (640, 0, 160, 300), (0, 300, 200, 300),
                (200, 300, 200, 300), (400, 300, 200, 300),
                (600, 300, 200, 300)]
        elif i == 9:
            assert self.c.layout.info()['layout_info'] == [
                (0, 0, 160, 300), (160, 0, 160, 300), (320, 0, 160, 300),
                (480, 0, 160, 300), (640, 0, 160, 300), (0, 300, 160, 300),
                (160, 300, 160, 300), (320, 300, 160, 300),
                (480, 300, 160, 300), (640, 300, 160, 300)]
        elif i == 10:
            assert self.c.layout.info()['layout_info'] == [
                (0, 0, 133, 300), (133, 0, 133, 300), (266, 0, 133, 300),
                (399, 0, 133, 300), (532, 0, 133, 300), (665, 0, 135, 300),
                (0, 300, 160, 300), (160, 300, 160, 300),
                (320, 300, 160, 300), (480, 300, 160, 300),
                (640, 300, 160, 300)]
        elif i == 11:
            assert self.c.layout.info()['layout_info'] == [
                (0, 0, 133, 300), (133, 0, 133, 300), (266, 0, 133, 300),
                (399, 0, 133, 300), (532, 0, 133, 300), (665, 0, 135, 300),
                (0, 300, 133, 300), (133, 300, 133, 300),
                (266, 300, 133, 300), (399, 300, 133, 300),
                (532, 300, 133, 300), (665, 300, 135, 300)]
        else:
            assert False


@Xephyr(False, RatioTileConfig())
def test_ratiotile_add_windows_golden_ratio(self):
    self.c.nextlayout()
    for i in range(12):
        self.testWindow(str(i))
        if i == 0:
            assert self.c.layout.info()['layout_info'] == [
                (0, 0, 800, 600)]
        elif i == 4:
            # the rest test col order
            assert self.c.layout.info()['layout_info'] == [
                (0, 0, 400, 200), (0, 200, 400, 200), (0, 400, 400, 200),
                (400, 0, 400, 300), (400, 300, 400, 300)]
        elif i == 5:
            assert self.c.layout.info()['layout_info'] == [
                (0, 0, 400, 200), (0, 200, 400, 200), (0, 400, 400, 200),
                (400, 0, 400, 200), (400, 200, 400, 200),
                (400, 400, 400, 200)]

        elif i == 9:
            assert self.c.layout.info()['layout_info'] == [
                (0, 0, 266, 150), (0, 150, 266, 150), (0, 300, 266, 150),
                (0, 450, 266, 150), (266, 0, 266, 150),
                (266, 150, 266, 150), (266, 300, 266, 150),
                (266, 450, 266, 150), (532, 0, 266, 300),
                (532, 300, 266, 300)]
        elif i == 10:
            assert self.c.layout.info()['layout_info'] == [
                (0, 0, 266, 150), (0, 150, 266, 150), (0, 300, 266, 150),
                (0, 450, 266, 150), (266, 0, 266, 150),
                (266, 150, 266, 150), (266, 300, 266, 150),
                (266, 450, 266, 150), (532, 0, 266, 200),
                (532, 200, 266, 200), (532, 400, 266, 200)]
        elif i == 11:
            assert self.c.layout.info()['layout_info'] == [
                (0, 0, 266, 150), (0, 150, 266, 150), (0, 300, 266, 150),
                (0, 450, 266, 150), (266, 0, 266, 150),
                (266, 150, 266, 150), (266, 300, 266, 150),
                (266, 450, 266, 150), (532, 0, 266, 150),
                (532, 150, 266, 150), (532, 300, 266, 150),
                (532, 450, 266, 150)]


@Xephyr(False, RatioTileConfig())
def test_ratiotile_basic(self):
    self.testWindow("one")
    self.testWindow("two")
    self.testWindow("three")
    sleep(0.1)
    assert self.c.window.info()['width'] == 264
    assert self.c.window.info()['height'] == 598
    assert self.c.window.info()['x'] == 0
    assert self.c.window.info()['y'] == 0
    assert self.c.window.info()['name'] == 'three'

    self.c.group.next_window()
    assert self.c.window.info()['width'] == 264
    assert self.c.window.info()['height'] == 598
    assert self.c.window.info()['x'] == 266
    assert self.c.window.info()['y'] == 0
    assert self.c.window.info()['name'] == 'two'

    self.c.group.next_window()
    assert self.c.window.info()['width'] == 266
    assert self.c.window.info()['height'] == 598
    assert self.c.window.info()['x'] == 532
    assert self.c.window.info()['y'] == 0
    assert self.c.window.info()['name'] == 'one'


class TileConfig:
    main = None
    groups = [
        libqtile.manager.Group("a"),
        libqtile.manager.Group("b"),
        libqtile.manager.Group("c"),
        libqtile.manager.Group("d")
    ]
    layouts = [
        layout.Tile(),
        layout.Tile(masterWindows=2)
        ]
    floating_layout = libqtile.layout.floating.Floating()
    keys = []
    mouse = []
    screens = []
    follow_mouse_focus = False


@Xephyr(False, TileConfig())
def test_tile_updown(self):
    self.testWindow("one")
    self.testWindow("two")
    self.testWindow("three")
    assert self.c.layout.info()["all"] == ["three", "two", "one"]
    self.c.layout.down()
    assert self.c.layout.info()["all"] == ["two", "one", "three"]
    self.c.layout.up()
    assert self.c.layout.info()["all"] == ["three", "two", "one"]


@Xephyr(False, TileConfig())
def test_tile_nextprev(self):
    self.testWindow("one")
    self.testWindow("two")
    self.testWindow("three")

    assert self.c.layout.info()["all"] == ["three", "two", "one"]
    assert self.c.groups()["a"]["focus"] == "three"

    self.c.layout.previous()
    assert self.c.groups()["a"]["focus"] == "two"

    self.c.layout.next()
    assert self.c.groups()["a"]["focus"] == "three"

    self.c.layout.next()
    assert self.c.groups()["a"]["focus"] == "one"

    self.c.layout.next()
    self.c.layout.next()
    self.c.layout.next()
    assert self.c.groups()["a"]["focus"] == "one"


@Xephyr(False, TileConfig())
def test_tile_master_and_slave(self):
    self.testWindow("one")
    self.testWindow("two")
    self.testWindow("three")

    assert self.c.layout.info()["master"] == ["three"]
    assert self.c.layout.info()["slave"] == ["two", "one"]

    self.c.nextlayout()
    assert self.c.layout.info()["master"] == ["three", "two"]
    assert self.c.layout.info()["slave"] == ["one"]


@Xephyr(False, TileConfig())
def test_tile_remove(self):
    one = self.testWindow("one")
    self.testWindow("two")
    three = self.testWindow("three")

    assert self.c.layout.info()["master"] == ["three"]
    self.kill(one)
    assert self.c.layout.info()["master"] == ["three"]
    self.kill(three)
    assert self.c.layout.info()["master"] == ["two"]


class SliceConfig:
    main = None
    groups = [
        libqtile.manager.Group("a"),
    ]
    layouts = [
        layout.Slice(side='left', width=200, wname='slice',
            fallback=layout.Stack(stacks=1, border_width=0)),
        layout.Slice(side='right', width=200, wname='slice',
            fallback=layout.Stack(stacks=1, border_width=0)),
        layout.Slice(side='top', width=200, wname='slice',
            fallback=layout.Stack(stacks=1, border_width=0)),
        layout.Slice(side='bottom', width=200, wname='slice',
            fallback=layout.Stack(stacks=1, border_width=0)),
        ]
    floating_layout = libqtile.layout.floating.Floating()
    keys = []
    mouse = []
    screens = []
    follow_mouse_focus = False


@Xephyr(False, SliceConfig())
def test_no_slice(self):
    self.testWindow('one')
    assertDimensions(self, 200, 0, 600, 600)
    self.testWindow('two')
    assertDimensions(self, 200, 0, 600, 600)


@Xephyr(False, SliceConfig())
def test_slice_first(self):
    self.testWindow('slice')
    assertDimensions(self, 0, 0, 200, 600)
    self.testWindow('two')
    assertDimensions(self, 200, 0, 600, 600)


@Xephyr(False, SliceConfig())
def test_slice_last(self):
    self.testWindow('one')
    assertDimensions(self, 200, 0, 600, 600)
    self.testWindow('slice')
    assertDimensions(self, 0, 0, 200, 600)


@Xephyr(False, SliceConfig())
def test_slice_focus(self):
    one = self.testWindow('one')
    assertFocused(self, 'one')
    two = self.testWindow('two')
    assertFocused(self, 'two')
    slice = self.testWindow('slice')
    assertFocused(self, 'slice')
    assertFocusPath(self, 'one', 'two', 'slice')
    three = self.testWindow('three')
    assertFocusPath(self, 'one', 'two', 'three', 'slice')
    self.kill(two)
    assertFocusPath(self, 'one', 'three', 'slice')
    self.kill(slice)
    assertFocusPath(self, 'one', 'three')
    slice = self.testWindow('slice')
    assertFocusPath(self, 'one', 'three', 'slice')


@Xephyr(False, SliceConfig())
def test_all_slices(self):
    self.testWindow('slice')  # left
    assertDimensions(self, 0, 0, 200, 600)
    self.c.nextlayout()  # right
    assertDimensions(self, 600, 0, 200, 600)
    self.c.nextlayout()  # top
    assertDimensions(self, 0, 0, 800, 200)
    self.c.nextlayout()  # bottom
    assertDimensions(self, 0, 400, 800, 200)
    self.c.nextlayout()  # left again
    self.testWindow('one')
    assertDimensions(self, 200, 0, 600, 600)
    self.c.nextlayout()  # right
    assertDimensions(self, 0, 0, 600, 600)
    self.c.nextlayout()  # top
    assertDimensions(self, 0, 200, 800, 400)
    self.c.nextlayout()  # bottom
    assertDimensions(self, 0, 0, 800, 400)


class ZoomyConfig:
    main = None
    groups = [
        libqtile.manager.Group("a"),
    ]
    layouts = [
        layout.Zoomy(columnwidth=200),
        ]
    floating_layout = libqtile.layout.floating.Floating()
    keys = []
    mouse = []
    screens = []


@Xephyr(False, ZoomyConfig())
def test_zoomy_one(self):
    self.testWindow('one')
    assertDimensions(self, 0, 0, 600, 600)
    self.testWindow('two')
    assertDimensions(self, 0, 0, 600, 600)
    self.testWindow('three')
    assertDimensions(self, 0, 0, 600, 600)
    assertFocusPath(self, 'one', 'two', 'three')
    # TODO(pc) find a way to check size of inactive windows
