import libqtile.manager
import libqtile.config
from libqtile import layout, bar, widget
from libqtile.config import Screen
from utils import Xephyr

LEFT_ALT = 'mod1'
WINDOWS = 'mod4'
FONTSIZE = 13
CHAM1 = '8AE234'
CHAM3 = '4E9A06'
GRAPH_KW = dict(line_width=1,
                graph_color=CHAM3,
                fill_color=CHAM3 + '.3',
                border_width=1,
                border_color=CHAM3
                )

# screens look like this
#     600         300
#  |-------------|-----|
#  |          480|     |580
#  |   A         |  B  |
#  |----------|--|     |
#  |       400|--|-----|
#  |   C      |        |400
#  |----------|   D    |
#     500     |--------|
#                 400
#
# Notice there is hole in the middle
# also that D goes down below the others


class FakeScreenConfig:
    auto_fullscreen = True
    main = None
    groups = [
        libqtile.config.Group("a"),
        libqtile.config.Group("b"),
        libqtile.config.Group("c"),
        libqtile.config.Group("d")
    ]
    layouts = [
        layout.Max(),
        layout.RatioTile(),
        layout.Tile(),
    ]
    floating_layout = libqtile.layout.floating.Floating()
    keys = []
    mouse = []
    fake_screens = [Screen(
        bottom=bar.Bar(
            [
                widget.GroupBox(this_screen_border=CHAM3,
                                borderwidth=1,
                                fontsize=FONTSIZE,
                                padding=1, margin_x=1, margin_y=1),
                widget.AGroupBox(),
                widget.Prompt(),
                widget.Sep(),
                widget.WindowName(
                    fontsize=FONTSIZE, margin_x=6),
                widget.Sep(),
                widget.CPUGraph(**GRAPH_KW),
                widget.MemoryGraph(**GRAPH_KW),
                widget.SwapGraph(foreground='20C020', **GRAPH_KW),
                widget.Sep(),
                widget.Systray(),
                widget.Sep(),
                widget.Clock(format='%H:%M:%S %d.%m.%Y',
                             fontsize=FONTSIZE, padding=6),
            ],
                    24,
            background="#555555"
        ),
        x=0, y=0, width=600, height=480
    ),
    Screen(
        top=bar.Bar(
            [
                        widget.GroupBox(),
                widget.WindowName(),
                widget.Clock()
            ],
                    30,
        ),
        x=600, y=0, width=300, height=580
    ),
    Screen(
        top=bar.Bar(
            [
                        widget.GroupBox(),
                widget.WindowName(),
                widget.Clock()
            ],
                    30,
        ),
           x=0, y=480, width=500, height=400),
                    Screen(
                        bottom=bar.Bar(
                            [
                        widget.GroupBox(),
                                widget.WindowName(),
                                widget.Clock()
                            ],
                    30,
                        ),
           x=500, y=580, width=400, height=400),
    ]

    screens = fake_screens


@Xephyr(False, FakeScreenConfig(), two_screens=False, width=900, height=980)
def test_basic(self):
    self.testWindow("zero")
    assert self.c.layout.info()["clients"] == ["zero"]
    assert self.c.screen.info() == {
        'y': 0, 'x': 0, 'index': 0, 'width': 600, 'height': 480}
    self.c.to_screen(1)
    self.testWindow("one")
    assert self.c.layout.info()["clients"] == ["one"]
    assert self.c.screen.info() == {
        'y': 0, 'x': 600, 'index': 1, 'width': 300, 'height': 580}
    self.c.to_screen(2)
    self.testXeyes()
    assert self.c.screen.info() == {
        'y': 480, 'x': 0, 'index': 2, 'width': 500, 'height': 400}
    self.c.to_screen(3)
    self.testXclock()
    assert self.c.screen.info() == {
        'y': 580, 'x': 500, 'index': 3, 'width': 400, 'height': 400}


@Xephyr(False, FakeScreenConfig(), two_screens=False, width=900, height=980)
def test_maximize_with_move_to_screen(self):
    """
    Ensure that maximize respects bars
    """
    self.testXclock()
    self.c.window.toggle_maximize()
    assert self.c.window.info()['width'] == 600
    assert self.c.window.info()['height'] == 456
    assert self.c.window.info()['x'] == 0
    assert self.c.window.info()['y'] == 0
    assert self.c.window.info()['group'] == 'a'

    # go to second screen
    self.c.to_screen(1)
    assert self.c.screen.info() == {
        'y': 0, 'x': 600, 'index': 1, 'width': 300, 'height': 580}
    assert self.c.group.info()['name'] == 'b'
    self.c.group['a'].toscreen()

    assert self.c.window.info()['width'] == 300
    assert self.c.window.info()['height'] == 550
    assert self.c.window.info()['x'] == 600
    assert self.c.window.info()['y'] == 30
    assert self.c.window.info()['group'] == 'a'


@Xephyr(False, FakeScreenConfig(), two_screens=False, width=900, height=980)
def test_float_first_on_second_screen(self):
    self.c.to_screen(1)
    assert self.c.screen.info() == {
        'y': 0, 'x': 600, 'index': 1, 'width': 300, 'height': 580}

    self.testXclock()
    self.c.window.toggle_floating()
    assert self.c.window.info()['width'] == 164
    assert self.c.window.info()['height'] == 164
    assert self.c.window.info()['x'] == 600
    assert self.c.window.info()['y'] == 0
    assert self.c.window.info()['group'] == 'b'
    assert self.c.window.info()['float_info'] == {
        'y': 0, 'x': 0, 'w': 164, 'h': 164}


@Xephyr(False, FakeScreenConfig(), two_screens=False, width=900, height=980)
def test_float_change_screens(self):
    #add some eyes, and float clock
    self.testXeyes()
    self.testXclock()
    self.c.window.toggle_floating()
    assert set(self.c.group.info()['windows']) == set(('xeyes', 'xclock'))
    assert self.c.group.info()['floating_info']['clients'] == ['xclock']
    assert self.c.window.info()['width'] == 164
    assert self.c.window.info()['height'] == 164
    assert self.c.window.info()['x'] == 0
    assert self.c.window.info()['y'] == 0
    assert self.c.window.info()['group'] == 'a'

    #put on group b
    assert self.c.screen.info() == {
        'y': 0, 'x': 0, 'index': 0, 'width': 600, 'height': 480}
    assert self.c.group.info()['name'] == 'a'
    self.c.to_screen(1)
    assert self.c.group.info()['name'] == 'b'
    assert self.c.screen.info() == {
        'y': 0, 'x': 600, 'index': 1, 'width': 300, 'height': 580}
    self.c.group['a'].toscreen()
    assert self.c.group.info()['name'] == 'a'
    assert set(self.c.group.info()['windows']) == set(('xeyes', 'xclock'))
    assert self.c.window.info()['name'] == 'xclock'
    assert self.c.window.info()['width'] == 164
    assert self.c.window.info()['height'] == 164
    assert self.c.window.info()['x'] == 600
    assert self.c.window.info()['y'] == 0
    assert self.c.window.info()['group'] == 'a'
    assert self.c.group.info()['floating_info']['clients'] == ['xclock']

    # move to screen 3
    self.c.to_screen(2)
    assert self.c.screen.info() == {
        'y': 480, 'x': 0, 'index': 2, 'width': 500, 'height': 400}
    assert self.c.group.info()['name'] == 'c'
    self.c.group['a'].toscreen()
    assert self.c.group.info()['name'] == 'a'
    assert set(self.c.group.info()['windows']) == set(('xeyes', 'xclock'))
    assert self.c.window.info()['name'] == 'xclock'
    assert self.c.window.info()['width'] == 164
    assert self.c.window.info()['height'] == 164
    assert self.c.window.info()['x'] == 0
    assert self.c.window.info()['y'] == 480

    # now screen 4 for fun
    self.c.to_screen(3)
    assert self.c.screen.info() == {
        'y': 580, 'x': 500, 'index': 3, 'width': 400, 'height': 400}
    assert self.c.group.info()['name'] == 'd'
    self.c.group['a'].toscreen()
    assert self.c.group.info()['name'] == 'a'
    assert set(self.c.group.info()['windows']) == set(('xeyes', 'xclock'))
    assert self.c.window.info()['name'] == 'xclock'
    assert self.c.window.info()['width'] == 164
    assert self.c.window.info()['height'] == 164
    assert self.c.window.info()['x'] == 500
    assert self.c.window.info()['y'] == 580

    # and back to one
    self.c.to_screen(0)
    assert self.c.screen.info() == {
        'y': 0, 'x': 0, 'index': 0, 'width': 600, 'height': 480}
    assert self.c.group.info()['name'] == 'b'
    self.c.group['a'].toscreen()
    assert self.c.group.info()['name'] == 'a'
    assert set(self.c.group.info()['windows']) == set(('xeyes', 'xclock'))
    assert self.c.window.info()['name'] == 'xclock'
    assert self.c.window.info()['width'] == 164
    assert self.c.window.info()['height'] == 164
    assert self.c.window.info()['x'] == 0
    assert self.c.window.info()['y'] == 0


@Xephyr(False, FakeScreenConfig(), two_screens=False, width=900, height=980)
def test_float_outside_edges(self):
    self.testXclock()
    self.c.window.toggle_floating()
    assert self.c.window.info()['width'] == 164
    assert self.c.window.info()['height'] == 164
    assert self.c.window.info()['x'] == 0
    assert self.c.window.info()['y'] == 0
    # empty because window is floating
    assert self.c.layout.info() == {
        'clients': [], 'group': 'a', 'name': 'max'}

    # move left, but some still on screen 0
    self.c.window.move_floating(-10, 20, 42, 42)
    assert self.c.window.info()['width'] == 164
    assert self.c.window.info()['height'] == 164
    assert self.c.window.info()['x'] == -10
    assert self.c.window.info()['y'] == 20
    assert self.c.window.info()['group'] == 'a'

    # move up, but some still on screen 0
    self.c.window.set_position_floating(-10, -20, 42, 42)
    assert self.c.window.info()['width'] == 164
    assert self.c.window.info()['height'] == 164
    assert self.c.window.info()['x'] == -10
    assert self.c.window.info()['y'] == -20
    assert self.c.window.info()['group'] == 'a'

    # move above a
    self.c.window.set_position_floating(50, -20, 42, 42)
    assert self.c.window.info()['width'] == 164
    assert self.c.window.info()['height'] == 164
    assert self.c.window.info()['x'] == 50
    assert self.c.window.info()['y'] == -20
    assert self.c.window.info()['group'] == 'a'

    # move down so still left, but next to screen c
    self.c.window.set_position_floating(-10, 520, 42, 42)
    assert self.c.window.info()['height'] == 164
    assert self.c.window.info()['x'] == -10
    assert self.c.window.info()['y'] == 520
    assert self.c.window.info()['group'] == 'c'

    # move above b
    self.c.window.set_position_floating(700, -10, 42, 42)
    assert self.c.window.info()['width'] == 164
    assert self.c.window.info()['height'] == 164
    assert self.c.window.info()['x'] == 700
    assert self.c.window.info()['y'] == -10
    assert self.c.window.info()['group'] == 'b'


@Xephyr(False, FakeScreenConfig(), two_screens=False, width=900, height=980)
def test_hammer_tile(self):
    # change to tile layout
    self.c.nextlayout()
    self.c.nextlayout()
    for i in range(7):
        self.testXclock()
    for i in range(30):
        old_group = (i + 1) % 4
        if old_group == 0:
            name = 'a'
        elif old_group == 1:
            name = 'b'
        elif old_group == 2:
            name = 'c'
        elif old_group == 3:
            name = 'd'

        self.c.to_screen((i + 1) % 4)
        self.c.group['a'].toscreen()
    assert self.c.group['a'].info()['windows'] == [
        'xclock', 'xclock', 'xclock', 'xclock',
        'xclock', 'xclock', 'xclock']


@Xephyr(False, FakeScreenConfig(), two_screens=False, width=900, height=980)
def test_hammer_ratio_tile(self):
    # change to ratio tile layout
    self.c.nextlayout()
    for i in range(7):
        self.testXclock()
    for i in range(30):
        old_group = (i + 1) % 4
        if old_group == 0:
            name = 'a'
        elif old_group == 1:
            name = 'b'
        elif old_group == 2:
            name = 'c'
        elif old_group == 3:
            name = 'd'

        self.c.to_screen((i + 1) % 4)
        self.c.group['a'].toscreen()
    assert self.c.group['a'].info()['windows'] == [
        'xclock', 'xclock', 'xclock', 'xclock',
        'xclock', 'xclock', 'xclock']


@Xephyr(False, FakeScreenConfig(), two_screens=False, width=900, height=980)
def test_ratio_to_fourth_screen(self):
    # change to ratio tile layout
    self.c.nextlayout()
    for i in range(7):
        self.testXclock()
    self.c.to_screen(1)
    self.c.group['a'].toscreen()
    assert self.c.group['a'].info()['windows'] == [
        'xclock', 'xclock', 'xclock', 'xclock',
        'xclock', 'xclock', 'xclock']

    # now move to 4th, fails...
    self.c.to_screen(3)
    self.c.group['a'].toscreen()
    assert self.c.group['a'].info()['windows'] == [
        'xclock', 'xclock', 'xclock', 'xclock',
        'xclock', 'xclock', 'xclock']
