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
from libqtile import bar, layout, widget
from libqtile.config import Screen
from libqtile.confreader import Config

LEFT_ALT = "mod1"
WINDOWS = "mod4"
FONTSIZE = 13
CHAM1 = "8AE234"
CHAM3 = "4E9A06"
GRAPH_KW = dict(
    line_width=1, graph_color=CHAM3, fill_color=CHAM3 + ".3", border_width=1, border_color=CHAM3
)

# screens look like this
#     500         300
#  |-------------|-----|
#  |          340|     |380
#  |   A         |  B  |
#  |----------|--|     |
#  |       220|--|-----|
#  |   C      |        |220
#  |----------|   D    |
#     450     |--------|
#                 350
#
# Notice there is a hole in the middle
# also D goes down below the others


class FakeScreenConfig(Config):
    auto_fullscreen = True
    groups = [
        libqtile.config.Group("a"),
        libqtile.config.Group("b"),
        libqtile.config.Group("c"),
        libqtile.config.Group("d"),
    ]
    layouts = [
        layout.Max(),
        layout.RatioTile(),
        layout.Tile(),
    ]
    floating_layout = libqtile.resources.default_config.floating_layout
    keys = []
    mouse = []
    fake_screens = [
        Screen(
            bottom=bar.Bar(
                [
                    widget.GroupBox(
                        this_screen_border=CHAM3,
                        borderwidth=1,
                        fontsize=FONTSIZE,
                        padding=1,
                        margin_x=1,
                        margin_y=1,
                    ),
                    widget.AGroupBox(),
                    widget.Prompt(),
                    widget.Sep(),
                    widget.WindowName(fontsize=FONTSIZE, margin_x=6),
                    widget.Sep(),
                    widget.CPUGraph(**GRAPH_KW),
                    widget.MemoryGraph(**GRAPH_KW),
                    widget.SwapGraph(foreground="20C020", **GRAPH_KW),
                    widget.Sep(),
                    widget.Clock(format="%H:%M:%S %d.%manager.%Y", fontsize=FONTSIZE, padding=6),
                ],
                24,
                background="#555555",
            ),
            left=bar.Gap(16),
            right=bar.Gap(20),
            x=0,
            y=0,
            width=500,
            height=340,
        ),
        Screen(
            top=bar.Bar(
                [widget.GroupBox(), widget.WindowName(), widget.Clock()],
                30,
            ),
            bottom=bar.Gap(24),
            left=bar.Gap(12),
            x=500,
            y=0,
            width=300,
            height=380,
        ),
        Screen(
            top=bar.Bar(
                [widget.GroupBox(), widget.WindowName(), widget.Clock()],
                30,
            ),
            bottom=bar.Gap(16),
            right=bar.Gap(40),
            x=0,
            y=340,
            width=450,
            height=220,
        ),
        Screen(
            top=bar.Bar(
                [widget.GroupBox(), widget.WindowName(), widget.Clock()],
                30,
            ),
            left=bar.Gap(20),
            right=bar.Gap(24),
            x=450,
            y=380,
            width=350,
            height=220,
        ),
    ]
    screens = []


fakescreen_config = pytest.mark.parametrize("manager", [FakeScreenConfig], indirect=True)


@fakescreen_config
def test_basic(manager):
    manager.test_window("zero")
    assert manager.c.layout.info()["clients"] == ["zero"]
    assert manager.c.screen.info() == {"y": 0, "x": 0, "index": 0, "width": 500, "height": 340}
    manager.c.to_screen(1)
    manager.test_window("one")
    assert manager.c.layout.info()["clients"] == ["one"]
    assert manager.c.screen.info() == {"y": 0, "x": 500, "index": 1, "width": 300, "height": 380}
    manager.c.to_screen(2)
    manager.test_window("two")
    assert manager.c.screen.info() == {"y": 340, "x": 0, "index": 2, "width": 450, "height": 220}
    manager.c.to_screen(3)
    manager.test_window("one")
    assert manager.c.screen.info() == {
        "y": 380,
        "x": 450,
        "index": 3,
        "width": 350,
        "height": 220,
    }


@fakescreen_config
def test_gaps(manager):
    g = manager.c.screens()[0]["gaps"]
    assert g["bottom"] == (0, 316, 500, 24)
    assert g["left"] == (0, 0, 16, 316)
    assert g["right"] == (480, 0, 20, 316)
    g = manager.c.screens()[1]["gaps"]
    assert g["top"] == (500, 0, 300, 30)
    assert g["bottom"] == (500, 356, 300, 24)
    assert g["left"] == (500, 30, 12, 326)
    g = manager.c.screens()[2]["gaps"]
    assert g["top"] == (0, 340, 450, 30)
    assert g["bottom"] == (0, 544, 450, 16)
    assert g["right"] == (410, 370, 40, 174)
    g = manager.c.screens()[3]["gaps"]
    assert g["top"] == (450, 380, 350, 30)
    assert g["left"] == (450, 410, 20, 190)
    assert g["right"] == (776, 410, 24, 190)


@fakescreen_config
def test_maximize_with_move_to_screen(manager):
    """Ensure that maximize respects bars"""
    manager.test_window("one")
    manager.c.window.toggle_maximize()
    assert manager.c.window.info()["width"] == 464
    assert manager.c.window.info()["height"] == 316
    assert manager.c.window.info()["x"] == 16
    assert manager.c.window.info()["y"] == 0
    assert manager.c.window.info()["group"] == "a"

    # go to second screen
    manager.c.to_screen(1)
    assert manager.c.screen.info() == {"y": 0, "x": 500, "index": 1, "width": 300, "height": 380}
    assert manager.c.group.info()["name"] == "b"
    manager.c.group["a"].toscreen()

    assert manager.c.window.info()["width"] == 288
    assert manager.c.window.info()["height"] == 326
    assert manager.c.window.info()["x"] == 512
    assert manager.c.window.info()["y"] == 30
    assert manager.c.window.info()["group"] == "a"


@fakescreen_config
def test_float_first_on_second_screen(manager):
    manager.c.to_screen(1)
    assert manager.c.screen.info() == {"y": 0, "x": 500, "index": 1, "width": 300, "height": 380}

    manager.test_window("one")
    # I don't know where y=30, x=12 comes from...
    assert manager.c.window.info()["float_info"] == {
        "y": 30,
        "x": 12,
        "width": 100,
        "height": 100,
    }

    manager.c.window.toggle_floating()
    assert manager.c.window.info()["width"] == 100
    assert manager.c.window.info()["height"] == 100

    assert manager.c.window.info()["x"] == 512
    assert manager.c.window.info()["y"] == 30
    assert manager.c.window.info()["group"] == "b"
    assert manager.c.window.info()["float_info"] == {
        "y": 30,
        "x": 12,
        "width": 100,
        "height": 100,
    }


@fakescreen_config
def test_float_change_screens(manager):
    # add one tiled and one floating window
    manager.test_window("tiled")
    manager.test_window("float")
    manager.c.window.toggle_floating()
    assert set(manager.c.group.info()["windows"]) == set(("tiled", "float"))
    assert manager.c.group.info()["floating_info"]["clients"] == ["float"]
    assert manager.c.window.info()["width"] == 100
    assert manager.c.window.info()["height"] == 100
    # 16 is given by the left gap width
    assert manager.c.window.info()["x"] == 16
    assert manager.c.window.info()["y"] == 0
    assert manager.c.window.info()["group"] == "a"

    # put on group b
    assert manager.c.screen.info() == {"y": 0, "x": 0, "index": 0, "width": 500, "height": 340}
    assert manager.c.group.info()["name"] == "a"
    manager.c.to_screen(1)
    assert manager.c.group.info()["name"] == "b"
    assert manager.c.screen.info() == {"y": 0, "x": 500, "index": 1, "width": 300, "height": 380}
    manager.c.group["a"].toscreen()
    assert manager.c.group.info()["name"] == "a"
    assert set(manager.c.group.info()["windows"]) == set(("tiled", "float"))
    assert manager.c.window.info()["name"] == "float"
    # width/height unchanged
    assert manager.c.window.info()["width"] == 100
    assert manager.c.window.info()["height"] == 100
    # x is shifted by 500, y is shifted by 0
    assert manager.c.window.info()["x"] == 516
    assert manager.c.window.info()["y"] == 0
    assert manager.c.window.info()["group"] == "a"
    assert manager.c.group.info()["floating_info"]["clients"] == ["float"]

    # move to screen 3
    manager.c.to_screen(2)
    assert manager.c.screen.info() == {"y": 340, "x": 0, "index": 2, "width": 450, "height": 220}
    assert manager.c.group.info()["name"] == "c"
    manager.c.group["a"].toscreen()
    assert manager.c.group.info()["name"] == "a"
    assert set(manager.c.group.info()["windows"]) == set(("tiled", "float"))
    assert manager.c.window.info()["name"] == "float"
    # width/height unchanged
    assert manager.c.window.info()["width"] == 100
    assert manager.c.window.info()["height"] == 100
    # x is shifted by 0, y is shifted by 340
    assert manager.c.window.info()["x"] == 16
    assert manager.c.window.info()["y"] == 340

    # now screen 4 for fun
    manager.c.to_screen(3)
    assert manager.c.screen.info() == {
        "y": 380,
        "x": 450,
        "index": 3,
        "width": 350,
        "height": 220,
    }
    assert manager.c.group.info()["name"] == "d"
    manager.c.group["a"].toscreen()
    assert manager.c.group.info()["name"] == "a"
    assert set(manager.c.group.info()["windows"]) == set(("tiled", "float"))
    assert manager.c.window.info()["name"] == "float"
    # width/height unchanged
    assert manager.c.window.info()["width"] == 100
    assert manager.c.window.info()["height"] == 100
    # x is shifted by 450, y is shifted by 40
    assert manager.c.window.info()["x"] == 466
    assert manager.c.window.info()["y"] == 380

    # and back to one
    manager.c.to_screen(0)
    assert manager.c.screen.info() == {"y": 0, "x": 0, "index": 0, "width": 500, "height": 340}
    assert manager.c.group.info()["name"] == "b"
    manager.c.group["a"].toscreen()
    assert manager.c.group.info()["name"] == "a"
    assert set(manager.c.group.info()["windows"]) == set(("tiled", "float"))
    assert manager.c.window.info()["name"] == "float"
    # back to the original location
    assert manager.c.window.info()["width"] == 100
    assert manager.c.window.info()["height"] == 100
    assert manager.c.window.info()["x"] == 16
    assert manager.c.window.info()["y"] == 0


@fakescreen_config
def test_float_outside_edges(manager):
    manager.test_window("one")
    manager.c.window.toggle_floating()
    assert manager.c.window.info()["width"] == 100
    assert manager.c.window.info()["height"] == 100
    # 16 is given by the left gap width
    assert manager.c.window.info()["x"] == 16
    assert manager.c.window.info()["y"] == 0
    # empty because window is floating
    assert manager.c.layout.info() == {"clients": [], "current": 0, "group": "a", "name": "max"}

    # move left, but some still on screen 0
    manager.c.window.move_floating(-30, 20)
    assert manager.c.window.info()["width"] == 100
    assert manager.c.window.info()["height"] == 100
    assert manager.c.window.info()["x"] == -14
    assert manager.c.window.info()["y"] == 20
    assert manager.c.window.info()["group"] == "a"

    # move up, but some still on screen 0
    manager.c.window.set_position_floating(-10, -20)
    assert manager.c.window.info()["width"] == 100
    assert manager.c.window.info()["height"] == 100
    assert manager.c.window.info()["x"] == -10
    assert manager.c.window.info()["y"] == -20
    assert manager.c.window.info()["group"] == "a"

    # move above a
    manager.c.window.set_position_floating(50, -20)
    assert manager.c.window.info()["width"] == 100
    assert manager.c.window.info()["height"] == 100
    assert manager.c.window.info()["x"] == 50
    assert manager.c.window.info()["y"] == -20
    assert manager.c.window.info()["group"] == "a"

    # move down so still left, but next to screen c
    manager.c.window.set_position_floating(-10, 360)
    assert manager.c.window.info()["height"] == 100
    assert manager.c.window.info()["x"] == -10
    assert manager.c.window.info()["y"] == 360
    assert manager.c.window.info()["group"] == "c"

    # move above b
    manager.c.window.set_position_floating(700, -10)
    assert manager.c.window.info()["width"] == 100
    assert manager.c.window.info()["height"] == 100
    assert manager.c.window.info()["x"] == 700
    assert manager.c.window.info()["y"] == -10
    assert manager.c.window.info()["group"] == "b"


@fakescreen_config
def test_hammer_tile(manager):
    # change to tile layout
    manager.c.next_layout()
    manager.c.next_layout()
    for i in range(7):
        manager.test_window("one")
    for i in range(30):

        manager.c.to_screen((i + 1) % 4)
        manager.c.group["a"].toscreen()
    assert manager.c.group["a"].info()["windows"] == [
        "one",
        "one",
        "one",
        "one",
        "one",
        "one",
        "one",
    ]


@fakescreen_config
def test_hammer_ratio_tile(manager):
    # change to ratio tile layout
    manager.c.next_layout()
    for i in range(7):
        manager.test_window("one")
    for i in range(30):
        manager.c.to_screen((i + 1) % 4)
        manager.c.group["a"].toscreen()
    assert manager.c.group["a"].info()["windows"] == [
        "one",
        "one",
        "one",
        "one",
        "one",
        "one",
        "one",
    ]


@fakescreen_config
def test_ratio_to_fourth_screen(manager):
    # change to ratio tile layout
    manager.c.next_layout()
    for i in range(7):
        manager.test_window("one")
    manager.c.to_screen(1)
    manager.c.group["a"].toscreen()
    assert manager.c.group["a"].info()["windows"] == [
        "one",
        "one",
        "one",
        "one",
        "one",
        "one",
        "one",
    ]

    # now move to 4th, fails...
    manager.c.to_screen(3)
    manager.c.group["a"].toscreen()
    assert manager.c.group["a"].info()["windows"] == [
        "one",
        "one",
        "one",
        "one",
        "one",
        "one",
        "one",
    ]
