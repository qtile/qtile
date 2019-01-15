# Copyright (c) 2011 Florian Mounier
# Copyright (c) 2012, 2014 Tycho Andersen
# Copyright (c) 2013 Craig Barnes
# Copyright (c) 2014 Sean Vig
# Copyright (c) 2014 Adi Sieker
# Copyright (c) 2014 Sebastien Blot
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import pytest

import libqtile.config
from libqtile import layout, bar, widget
from libqtile.config import Screen

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
# Notice there is a hole in the middle
# also D goes down below the others


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
    fake_screens = [
        Screen(
            bottom=bar.Bar(
                [
                    widget.GroupBox(this_screen_border=CHAM3,
                                    borderwidth=1,
                                    fontsize=FONTSIZE,
                                    padding=1, margin_x=1, margin_y=1),
                    widget.AGroupBox(),
                    widget.Prompt(),
                    widget.Sep(),
                    widget.WindowName(fontsize=FONTSIZE, margin_x=6),
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
            left=bar.Gap(16),
            right=bar.Gap(20),
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
            bottom=bar.Gap(24),
            left=bar.Gap(12),
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
            bottom=bar.Gap(16),
            right=bar.Gap(40),
            x=0, y=480, width=500, height=400
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
            left=bar.Gap(20),
            right=bar.Gap(24),
            x=500, y=580, width=400, height=400
        ),
    ]
    screens = []


xephyr_config = {
    "xinerama": False,
    "two_screens": False,
    "width": 900,
    "height": 980
}
fakescreen_config = pytest.mark.parametrize("xephyr, qtile", [(xephyr_config, FakeScreenConfig)], indirect=True)


@fakescreen_config
def test_basic(qtile):
    qtile.test_window("zero")
    assert qtile.c.layout.info()["clients"] == ["zero"]
    assert qtile.c.screen.info() == {
        'y': 0, 'x': 0, 'index': 0, 'width': 600, 'height': 480}
    qtile.c.to_screen(1)
    qtile.test_window("one")
    assert qtile.c.layout.info()["clients"] == ["one"]
    assert qtile.c.screen.info() == {
        'y': 0, 'x': 600, 'index': 1, 'width': 300, 'height': 580}
    qtile.c.to_screen(2)
    qtile.test_xeyes()
    assert qtile.c.screen.info() == {
        'y': 480, 'x': 0, 'index': 2, 'width': 500, 'height': 400}
    qtile.c.to_screen(3)
    qtile.test_xclock()
    assert qtile.c.screen.info() == {'y': 580, 'x': 500, 'index': 3, 'width': 400, 'height': 400}


@fakescreen_config
def test_gaps(qtile):
    g = qtile.c.screens()[0]["gaps"]
    assert g["bottom"] == (0, 456, 600, 24)
    assert g["left"] == (0, 0, 16, 456)
    assert g["right"] == (580, 0, 20, 456)
    g = qtile.c.screens()[1]["gaps"]
    assert g["top"] == (600, 0, 300, 30)
    assert g["bottom"] == (600, 556, 300, 24)
    assert g["left"] == (600, 30, 12, 526)
    g = qtile.c.screens()[2]["gaps"]
    assert g["top"] == (0, 480, 500, 30)
    assert g["bottom"] == (0, 864, 500, 16)
    assert g["right"] == (460, 510, 40, 354)
    g = qtile.c.screens()[3]["gaps"]
    assert g["top"] == (500, 580, 400, 30)
    assert g["left"] == (500, 610, 20, 370)
    assert g["right"] == (876, 610, 24, 370)


@fakescreen_config
def test_maximize_with_move_to_screen(qtile):
    """Ensure that maximize respects bars"""
    qtile.test_xclock()
    qtile.c.window.toggle_maximize()
    assert qtile.c.window.info()['width'] == 564
    assert qtile.c.window.info()['height'] == 456
    assert qtile.c.window.info()['x'] == 16
    assert qtile.c.window.info()['y'] == 0
    assert qtile.c.window.info()['group'] == 'a'

    # go to second screen
    qtile.c.to_screen(1)
    assert qtile.c.screen.info() == {
        'y': 0, 'x': 600, 'index': 1, 'width': 300, 'height': 580}
    assert qtile.c.group.info()['name'] == 'b'
    qtile.c.group['a'].toscreen()

    assert qtile.c.window.info()['width'] == 288
    assert qtile.c.window.info()['height'] == 526
    assert qtile.c.window.info()['x'] == 612
    assert qtile.c.window.info()['y'] == 30
    assert qtile.c.window.info()['group'] == 'a'


@fakescreen_config
def test_float_first_on_second_screen(qtile):
    qtile.c.to_screen(1)
    assert qtile.c.screen.info() == {
        'y': 0, 'x': 600, 'index': 1, 'width': 300, 'height': 580}

    qtile.test_xclock()
    # I don't know where y=30, x=12 comes from...
    assert qtile.c.window.info()['float_info'] == {
        'y': 30, 'x': 12, 'width': 164, 'height': 164
    }

    qtile.c.window.toggle_floating()
    assert qtile.c.window.info()['width'] == 164
    assert qtile.c.window.info()['height'] == 164

    assert qtile.c.window.info()['x'] == 612
    assert qtile.c.window.info()['y'] == 30
    assert qtile.c.window.info()['group'] == 'b'
    assert qtile.c.window.info()['float_info'] == {
        'y': 30, 'x': 12, 'width': 164, 'height': 164
    }


@fakescreen_config
def test_float_change_screens(qtile):
    # add some eyes, and float clock
    qtile.test_xeyes()
    qtile.test_xclock()
    qtile.c.window.toggle_floating()
    assert set(qtile.c.group.info()['windows']) == set(('xeyes', 'xclock'))
    assert qtile.c.group.info()['floating_info']['clients'] == ['xclock']
    assert qtile.c.window.info()['width'] == 164
    assert qtile.c.window.info()['height'] == 164
    # 16 is given by the left gap width
    assert qtile.c.window.info()['x'] == 16
    assert qtile.c.window.info()['y'] == 0
    assert qtile.c.window.info()['group'] == 'a'

    # put on group b
    assert qtile.c.screen.info() == {
        'y': 0, 'x': 0, 'index': 0, 'width': 600, 'height': 480}
    assert qtile.c.group.info()['name'] == 'a'
    qtile.c.to_screen(1)
    assert qtile.c.group.info()['name'] == 'b'
    assert qtile.c.screen.info() == {
        'y': 0, 'x': 600, 'index': 1, 'width': 300, 'height': 580}
    qtile.c.group['a'].toscreen()
    assert qtile.c.group.info()['name'] == 'a'
    assert set(qtile.c.group.info()['windows']) == set(('xeyes', 'xclock'))
    assert qtile.c.window.info()['name'] == 'xclock'
    # width/height unchanged
    assert qtile.c.window.info()['width'] == 164
    assert qtile.c.window.info()['height'] == 164
    # x is shifted by 600, y is shifted by 0
    assert qtile.c.window.info()['x'] == 616
    assert qtile.c.window.info()['y'] == 0
    assert qtile.c.window.info()['group'] == 'a'
    assert qtile.c.group.info()['floating_info']['clients'] == ['xclock']

    # move to screen 3
    qtile.c.to_screen(2)
    assert qtile.c.screen.info() == {
        'y': 480, 'x': 0, 'index': 2, 'width': 500, 'height': 400}
    assert qtile.c.group.info()['name'] == 'c'
    qtile.c.group['a'].toscreen()
    assert qtile.c.group.info()['name'] == 'a'
    assert set(qtile.c.group.info()['windows']) == set(('xeyes', 'xclock'))
    assert qtile.c.window.info()['name'] == 'xclock'
    # width/height unchanged
    assert qtile.c.window.info()['width'] == 164
    assert qtile.c.window.info()['height'] == 164
    # x is shifted by 0, y is shifted by 480
    assert qtile.c.window.info()['x'] == 16
    assert qtile.c.window.info()['y'] == 480

    # now screen 4 for fun
    qtile.c.to_screen(3)
    assert qtile.c.screen.info() == {
        'y': 580, 'x': 500, 'index': 3, 'width': 400, 'height': 400}
    assert qtile.c.group.info()['name'] == 'd'
    qtile.c.group['a'].toscreen()
    assert qtile.c.group.info()['name'] == 'a'
    assert set(qtile.c.group.info()['windows']) == set(('xeyes', 'xclock'))
    assert qtile.c.window.info()['name'] == 'xclock'
    # width/height unchanged
    assert qtile.c.window.info()['width'] == 164
    assert qtile.c.window.info()['height'] == 164
    # x is shifted by 500, y is shifted by 580
    assert qtile.c.window.info()['x'] == 516
    assert qtile.c.window.info()['y'] == 580

    # and back to one
    qtile.c.to_screen(0)
    assert qtile.c.screen.info() == {
        'y': 0, 'x': 0, 'index': 0, 'width': 600, 'height': 480}
    assert qtile.c.group.info()['name'] == 'b'
    qtile.c.group['a'].toscreen()
    assert qtile.c.group.info()['name'] == 'a'
    assert set(qtile.c.group.info()['windows']) == set(('xeyes', 'xclock'))
    assert qtile.c.window.info()['name'] == 'xclock'
    # back to the original location
    assert qtile.c.window.info()['width'] == 164
    assert qtile.c.window.info()['height'] == 164
    assert qtile.c.window.info()['x'] == 16
    assert qtile.c.window.info()['y'] == 0


@fakescreen_config
def test_float_outside_edges(qtile):
    qtile.test_xclock()
    qtile.c.window.toggle_floating()
    assert qtile.c.window.info()['width'] == 164
    assert qtile.c.window.info()['height'] == 164
    # 16 is given by the left gap width
    assert qtile.c.window.info()['x'] == 16
    assert qtile.c.window.info()['y'] == 0
    # empty because window is floating
    assert qtile.c.layout.info() == {
        'clients': [], 'current': 0, 'group': 'a', 'name': 'max'}

    # move left, but some still on screen 0
    qtile.c.window.move_floating(-30, 20, 42, 42)
    assert qtile.c.window.info()['width'] == 164
    assert qtile.c.window.info()['height'] == 164
    assert qtile.c.window.info()['x'] == -14
    assert qtile.c.window.info()['y'] == 20
    assert qtile.c.window.info()['group'] == 'a'

    # move up, but some still on screen 0
    qtile.c.window.set_position_floating(-10, -20, 42, 42)
    assert qtile.c.window.info()['width'] == 164
    assert qtile.c.window.info()['height'] == 164
    assert qtile.c.window.info()['x'] == -10
    assert qtile.c.window.info()['y'] == -20
    assert qtile.c.window.info()['group'] == 'a'

    # move above a
    qtile.c.window.set_position_floating(50, -20, 42, 42)
    assert qtile.c.window.info()['width'] == 164
    assert qtile.c.window.info()['height'] == 164
    assert qtile.c.window.info()['x'] == 50
    assert qtile.c.window.info()['y'] == -20
    assert qtile.c.window.info()['group'] == 'a'

    # move down so still left, but next to screen c
    qtile.c.window.set_position_floating(-10, 520, 42, 42)
    assert qtile.c.window.info()['height'] == 164
    assert qtile.c.window.info()['x'] == -10
    assert qtile.c.window.info()['y'] == 520
    assert qtile.c.window.info()['group'] == 'c'

    # move above b
    qtile.c.window.set_position_floating(700, -10, 42, 42)
    assert qtile.c.window.info()['width'] == 164
    assert qtile.c.window.info()['height'] == 164
    assert qtile.c.window.info()['x'] == 700
    assert qtile.c.window.info()['y'] == -10
    assert qtile.c.window.info()['group'] == 'b'


@fakescreen_config
def test_hammer_tile(qtile):
    # change to tile layout
    qtile.c.next_layout()
    qtile.c.next_layout()
    for i in range(7):
        qtile.test_xclock()
    for i in range(30):

        qtile.c.to_screen((i + 1) % 4)
        qtile.c.group['a'].toscreen()
    assert qtile.c.group['a'].info()['windows'] == [
        'xclock', 'xclock', 'xclock', 'xclock',
        'xclock', 'xclock', 'xclock']


@fakescreen_config
def test_hammer_ratio_tile(qtile):
    # change to ratio tile layout
    qtile.c.next_layout()
    for i in range(7):
        qtile.test_xclock()
    for i in range(30):
        qtile.c.to_screen((i + 1) % 4)
        qtile.c.group['a'].toscreen()
    assert qtile.c.group['a'].info()['windows'] == [
        'xclock', 'xclock', 'xclock', 'xclock',
        'xclock', 'xclock', 'xclock']


@fakescreen_config
def test_ratio_to_fourth_screen(qtile):
    # change to ratio tile layout
    qtile.c.next_layout()
    for i in range(7):
        qtile.test_xclock()
    qtile.c.to_screen(1)
    qtile.c.group['a'].toscreen()
    assert qtile.c.group['a'].info()['windows'] == [
        'xclock', 'xclock', 'xclock', 'xclock',
        'xclock', 'xclock', 'xclock']

    # now move to 4th, fails...
    qtile.c.to_screen(3)
    qtile.c.group['a'].toscreen()
    assert qtile.c.group['a'].info()['windows'] == [
        'xclock', 'xclock', 'xclock', 'xclock',
        'xclock', 'xclock', 'xclock']
