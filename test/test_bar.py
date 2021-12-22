# Copyright (c) 2011 Florian Mounier
# Copyright (c) 2012-2013 Craig Barnes
# Copyright (c) 2012 roger
# Copyright (c) 2012, 2014-2015 Tycho Andersen
# Copyright (c) 2014 Sean Vig
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

import os
import tempfile
from pathlib import Path

import pytest

import libqtile.bar
import libqtile.config
import libqtile.confreader
import libqtile.layout
import libqtile.widget
from libqtile.command.base import CommandError
from test.helpers import Retry


class GBConfig(libqtile.confreader.Config):
    auto_fullscreen = True
    keys = []
    mouse = []
    groups = [
        libqtile.config.Group("a"),
        libqtile.config.Group("bb"),
        libqtile.config.Group("ccc"),
        libqtile.config.Group("dddd"),
        libqtile.config.Group("Pppy"),
    ]
    layouts = [libqtile.layout.stack.Stack(num_stacks=1)]
    floating_layout = libqtile.resources.default_config.floating_layout
    screens = [
        libqtile.config.Screen(
            top=libqtile.bar.Bar(
                [
                    libqtile.widget.CPUGraph(
                        width=libqtile.bar.STRETCH,
                        type="linefill",
                        border_width=20,
                        margin_x=1,
                        margin_y=1,
                    ),
                    libqtile.widget.MemoryGraph(type="line"),
                    libqtile.widget.SwapGraph(type="box"),
                    libqtile.widget.TextBox(name="text", background="333333"),
                ],
                50,
            ),
            bottom=libqtile.bar.Bar(
                [
                    libqtile.widget.GroupBox(),
                    libqtile.widget.AGroupBox(),
                    libqtile.widget.Prompt(),
                    libqtile.widget.WindowName(),
                    libqtile.widget.Sep(),
                    libqtile.widget.Clock(),
                ],
                50,
            ),
            # TODO: Add vertical bars and test widgets that support them
        )
    ]


gb_config = pytest.mark.parametrize("manager", [GBConfig], indirect=True)


def test_completion():
    c = libqtile.widget.prompt.CommandCompleter(None, True)
    c.reset()
    c.lookup = [
        ("a", "x/a"),
        ("aa", "x/aa"),
    ]
    assert c.complete("a") == "a"
    assert c.actual() == "x/a"
    assert c.complete("a") == "aa"
    assert c.complete("a") == "a"

    c = libqtile.widget.prompt.CommandCompleter(None)
    r = c.complete("l")
    assert c.actual().endswith(r)

    c.reset()
    assert c.complete("/bi") == "/bin/"
    c.reset()
    assert c.complete("/bin") != "/bin/"
    c.reset()

    home_dir = os.path.expanduser("~")
    with tempfile.TemporaryDirectory(prefix="qtile_test_", dir=home_dir) as absolute_tmp_path:
        tmp_dirname = absolute_tmp_path[len(home_dir + os.sep) :]
        user_input = os.path.join("~", tmp_dirname)
        assert c.complete(user_input) == user_input

        c.reset()
        test_bin_dir = os.path.join(absolute_tmp_path, "qtile-test-bin")
        os.mkdir(test_bin_dir)
        assert c.complete(user_input) == os.path.join(user_input, "qtile-test-bin") + os.sep

    c.reset()
    s = "thisisatotallynonexistantpathforsure"
    assert c.complete(s) == s
    assert c.actual() == s
    c.reset()


@gb_config
def test_draw(manager):
    manager.test_window("one")
    b = manager.c.bar["bottom"].info()
    assert b["widgets"][0]["name"] == "groupbox"


@gb_config
def test_prompt(manager, monkeypatch):
    assert manager.c.widget["prompt"].info()["width"] == 0
    manager.c.spawncmd(":")
    manager.c.widget["prompt"].fake_keypress("a")
    manager.c.widget["prompt"].fake_keypress("Tab")

    manager.c.spawncmd(":")
    manager.c.widget["prompt"].fake_keypress("slash")
    manager.c.widget["prompt"].fake_keypress("Tab")

    script = Path(__file__).parent / "scripts" / "window.py"
    manager.c.spawncmd(":", aliases={"w": script.as_posix()})
    manager.c.widget["prompt"].fake_keypress("w")
    manager.c.widget["prompt"].fake_keypress("Return")

    @Retry(ignore_exceptions=(CommandError,))
    def is_spawned():
        return manager.c.window.info()

    is_spawned()


@gb_config
def test_event(manager):
    manager.c.group["bb"].toscreen()


@gb_config
def test_textbox(manager):
    assert "text" in manager.c.list_widgets()
    s = "some text"
    manager.c.widget["text"].update(s)
    assert manager.c.widget["text"].get() == s
    s = "Aye, much longer string than the initial one"
    manager.c.widget["text"].update(s)
    assert manager.c.widget["text"].get() == s
    manager.c.group["Pppy"].toscreen()
    manager.c.widget["text"].set_font(fontsize=12)


@gb_config
def test_textbox_errors(manager):
    manager.c.widget["text"].update(None)
    manager.c.widget["text"].update("".join(chr(i) for i in range(255)))
    manager.c.widget["text"].update("V\xE2r\xE2na\xE7\xEE")
    manager.c.widget["text"].update("\ua000")


@gb_config
def test_groupbox_button_press(manager):
    manager.c.group["ccc"].toscreen()
    assert manager.c.groups()["a"]["screen"] is None
    manager.c.bar["bottom"].fake_button_press(0, "bottom", 10, 10, 1)
    assert manager.c.groups()["a"]["screen"] == 0


class GeomConf(libqtile.confreader.Config):
    auto_fullscreen = False
    keys = []
    mouse = []
    groups = [
        libqtile.config.Group("a"),
        libqtile.config.Group("b"),
        libqtile.config.Group("c"),
        libqtile.config.Group("d"),
    ]
    layouts = [libqtile.layout.stack.Stack(num_stacks=1)]
    floating_layout = libqtile.resources.default_config.floating_layout
    screens = [
        libqtile.config.Screen(
            top=libqtile.bar.Bar([], 10),
            bottom=libqtile.bar.Bar([], 10),
            left=libqtile.bar.Bar([], 10),
            right=libqtile.bar.Bar([], 10),
        )
    ]


geom_config = pytest.mark.parametrize("manager", [GeomConf], indirect=True)


class DBarH(libqtile.bar.Bar):
    def __init__(self, widgets, size):
        libqtile.bar.Bar.__init__(self, widgets, size)
        self.horizontal = True


class DBarV(libqtile.bar.Bar):
    def __init__(self, widgets, size):
        libqtile.bar.Bar.__init__(self, widgets, size)
        self.horizontal = False


class DWidget:
    def __init__(self, length, length_type):
        self.length, self.length_type = length, length_type


@geom_config
def test_geometry(manager):
    manager.test_window("one")
    g = manager.c.screens()[0]["gaps"]
    assert g["top"] == (0, 0, 800, 10)
    assert g["bottom"] == (0, 590, 800, 10)
    assert g["left"] == (0, 10, 10, 580)
    assert g["right"] == (790, 10, 10, 580)
    assert len(manager.c.windows()) == 1
    geom = manager.c.windows()[0]
    assert geom["x"] == 10
    assert geom["y"] == 10
    assert geom["width"] == 778
    assert geom["height"] == 578
    internal = manager.c.internal_windows()
    assert len(internal) == 4


@geom_config
def test_resize(manager):
    def wd(dwidget_list):
        return [i.length for i in dwidget_list]

    def offx(dwidget_list):
        return [i.offsetx for i in dwidget_list]

    def offy(dwidget_list):
        return [i.offsety for i in dwidget_list]

    for DBar, off in ((DBarH, offx), (DBarV, offy)):  # noqa: N806
        b = DBar([], 100)

        dwidget_list = [
            DWidget(10, libqtile.bar.CALCULATED),
            DWidget(None, libqtile.bar.STRETCH),
            DWidget(None, libqtile.bar.STRETCH),
            DWidget(10, libqtile.bar.CALCULATED),
        ]
        b._resize(100, dwidget_list)
        assert wd(dwidget_list) == [10, 40, 40, 10]
        assert off(dwidget_list) == [0, 10, 50, 90]

        b._resize(101, dwidget_list)
        assert wd(dwidget_list) == [10, 41, 40, 10]
        assert off(dwidget_list) == [0, 10, 51, 91]

        dwidget_list = [DWidget(10, libqtile.bar.CALCULATED)]
        b._resize(100, dwidget_list)
        assert wd(dwidget_list) == [10]
        assert off(dwidget_list) == [0]

        dwidget_list = [DWidget(10, libqtile.bar.CALCULATED), DWidget(None, libqtile.bar.STRETCH)]
        b._resize(100, dwidget_list)
        assert wd(dwidget_list) == [10, 90]
        assert off(dwidget_list) == [0, 10]

        dwidget_list = [
            DWidget(None, libqtile.bar.STRETCH),
            DWidget(10, libqtile.bar.CALCULATED),
        ]
        b._resize(100, dwidget_list)
        assert wd(dwidget_list) == [90, 10]
        assert off(dwidget_list) == [0, 90]

        dwidget_list = [
            DWidget(10, libqtile.bar.CALCULATED),
            DWidget(None, libqtile.bar.STRETCH),
            DWidget(10, libqtile.bar.CALCULATED),
        ]
        b._resize(100, dwidget_list)
        assert wd(dwidget_list) == [10, 80, 10]
        assert off(dwidget_list) == [0, 10, 90]


class ExampleWidget(libqtile.widget.base._Widget):
    orientations = libqtile.widget.base.ORIENTATION_HORIZONTAL

    def __init__(self):
        libqtile.widget.base._Widget.__init__(self, 10)

    def draw(self):
        pass


class BrokenWidget(libqtile.widget.base._Widget):
    def __init__(self, exception_class, **config):
        libqtile.widget.base._Widget.__init__(self, 10, **config)
        self.exception_class = exception_class

    def _configure(self, qtile, bar):
        raise self.exception_class


def test_basic(manager_nospawn):
    config = GeomConf
    config.screens = [
        libqtile.config.Screen(
            bottom=libqtile.bar.Bar(
                [
                    ExampleWidget(),
                    libqtile.widget.Spacer(libqtile.bar.STRETCH),
                    ExampleWidget(),
                    libqtile.widget.Spacer(libqtile.bar.STRETCH),
                    ExampleWidget(),
                    libqtile.widget.Spacer(libqtile.bar.STRETCH),
                    ExampleWidget(),
                ],
                10,
            )
        )
    ]

    manager_nospawn.start(config)

    i = manager_nospawn.c.bar["bottom"].info()
    assert i["widgets"][0]["offset"] == 0
    assert i["widgets"][1]["offset"] == 10
    assert i["widgets"][1]["width"] == 252
    assert i["widgets"][2]["offset"] == 262
    assert i["widgets"][3]["offset"] == 272
    assert i["widgets"][3]["width"] == 256
    assert i["widgets"][4]["offset"] == 528
    assert i["widgets"][5]["offset"] == 538
    assert i["widgets"][5]["width"] == 252
    assert i["widgets"][6]["offset"] == 790
    libqtile.hook.clear()


def test_singlespacer(manager_nospawn):
    config = GeomConf
    config.screens = [
        libqtile.config.Screen(
            bottom=libqtile.bar.Bar(
                [
                    libqtile.widget.Spacer(libqtile.bar.STRETCH),
                ],
                10,
            )
        )
    ]

    manager_nospawn.start(config)

    i = manager_nospawn.c.bar["bottom"].info()
    assert i["widgets"][0]["offset"] == 0
    assert i["widgets"][0]["width"] == 800
    libqtile.hook.clear()


def test_nospacer(manager_nospawn):
    config = GeomConf
    config.screens = [
        libqtile.config.Screen(bottom=libqtile.bar.Bar([ExampleWidget(), ExampleWidget()], 10))
    ]

    manager_nospawn.start(config)

    i = manager_nospawn.c.bar["bottom"].info()
    assert i["widgets"][0]["offset"] == 0
    assert i["widgets"][1]["offset"] == 10
    libqtile.hook.clear()


def test_consecutive_spacer(manager_nospawn):
    config = GeomConf
    config.screens = [
        libqtile.config.Screen(
            bottom=libqtile.bar.Bar(
                [
                    ExampleWidget(),  # Left
                    libqtile.widget.Spacer(libqtile.bar.STRETCH),
                    libqtile.widget.Spacer(libqtile.bar.STRETCH),
                    ExampleWidget(),  # Centre
                    ExampleWidget(),
                    libqtile.widget.Spacer(libqtile.bar.STRETCH),
                    ExampleWidget(),  # Right
                ],
                10,
            )
        )
    ]

    manager_nospawn.start(config)

    i = manager_nospawn.c.bar["bottom"].info()
    assert i["widgets"][0]["offset"] == 0
    assert i["widgets"][0]["width"] == 10
    assert i["widgets"][1]["offset"] == 10
    assert i["widgets"][1]["width"] == 190
    assert i["widgets"][2]["offset"] == 200
    assert i["widgets"][2]["width"] == 190
    assert i["widgets"][3]["offset"] == 390
    assert i["widgets"][3]["width"] == 10
    assert i["widgets"][4]["offset"] == 400
    assert i["widgets"][4]["width"] == 10
    assert i["widgets"][5]["offset"] == 410
    assert i["widgets"][5]["width"] == 380
    assert i["widgets"][6]["offset"] == 790
    assert i["widgets"][6]["width"] == 10
    libqtile.hook.clear()


def test_configure_broken_widgets(manager_nospawn):
    config = GeomConf

    widget_list = [
        BrokenWidget(ValueError),
        BrokenWidget(IndexError),
        BrokenWidget(IndentationError),
        BrokenWidget(TypeError),
        BrokenWidget(NameError),
        BrokenWidget(ImportError),
        libqtile.widget.Spacer(libqtile.bar.STRETCH),
    ]

    config.screens = [libqtile.config.Screen(bottom=libqtile.bar.Bar(widget_list, 10))]

    manager_nospawn.start(config)

    i = manager_nospawn.c.bar["bottom"].info()

    # Check that we have same number of widgets
    assert len(i["widgets"]) == len(widget_list)

    # Check each broken widget is replaced
    for index, widget in enumerate(widget_list):
        if isinstance(widget, BrokenWidget):
            assert i["widgets"][index]["name"] == "configerrorwidget"


def test_bar_hide_show_with_margin(manager_nospawn):
    """Check :
        - the height of a horizontal bar with its margins,
        - the ordinate of a unique window.
    after 3 successive actions :
        - creation
        - hidding the bar
        - unhidding the bar
    """
    config = GeomConf

    config.screens = [libqtile.config.Screen(top=libqtile.bar.Bar([], 12, margin=[5, 5, 5, 5]))]

    manager_nospawn.start(config)
    manager_nospawn.test_window("w")

    assert manager_nospawn.c.bar["top"].info().get("size") == 22
    assert manager_nospawn.c.windows()[0]["y"] == 22

    manager_nospawn.c.hide_show_bar("top")
    assert manager_nospawn.c.bar["top"].info().get("size") == 0
    assert manager_nospawn.c.windows()[0]["y"] == 0

    manager_nospawn.c.hide_show_bar("top")
    assert manager_nospawn.c.bar["top"].info().get("size") == 22
    assert manager_nospawn.c.windows()[0]["y"] == 22


def test_bar_border_horizontal(manager_nospawn):
    config = GeomConf

    config.screens = [
        libqtile.config.Screen(
            top=libqtile.bar.Bar(
                [libqtile.widget.Spacer()],
                12,
                margin=5,
                border_width=5,
            ),
            bottom=libqtile.bar.Bar(
                [libqtile.widget.Spacer()],
                12,
                margin=5,
                border_width=0,
            ),
        )
    ]

    manager_nospawn.start(config)

    top_info = manager_nospawn.c.bar["top"].info
    bottom_info = manager_nospawn.c.bar["bottom"].info

    # Screen is 800px wide so:
    # -top bar should have width of 800 - 5 - 5 - 5 - 5 = 780 (margin and border)
    # -bottom bar should have width of 800 - 5 - 5 = 790 (margin and no border)

    assert top_info()["width"] == 780
    assert bottom_info()["width"] == 790

    # Bar "height" should still be the value set in the config but "size" is
    # adjusted for margin and border:
    # -top bar should have size of 12 + 5 + 5 + 5 + 5 = 32 (margin and border)
    # -bottom bar should have size of 12 + 5 + 5 = 22 (margin and border)

    assert top_info()["height"] == 12
    assert top_info()["size"] == 32
    assert bottom_info()["height"] == 12
    assert bottom_info()["size"] == 22

    # Test widget offsets
    # Where there is a border, widget should be offset by that amount

    _, xoffset = manager_nospawn.c.bar["top"].eval("self.widgets[0].offsetx")
    assert xoffset == "5"

    _, yoffset = manager_nospawn.c.bar["top"].eval("self.widgets[0].offsety")
    assert xoffset == "5"

    # Where there is no border, this should be 0
    _, xoffset = manager_nospawn.c.bar["bottom"].eval("self.widgets[0].offsetx")
    assert xoffset == "0"

    _, yoffset = manager_nospawn.c.bar["bottom"].eval("self.widgets[0].offsety")
    assert xoffset == "0"


def test_bar_border_vertical(manager_nospawn):
    config = GeomConf

    config.screens = [
        libqtile.config.Screen(
            left=libqtile.bar.Bar(
                [libqtile.widget.Spacer()],
                12,
                margin=5,
                border_width=5,
            ),
            right=libqtile.bar.Bar(
                [libqtile.widget.Spacer()],
                12,
                margin=5,
                border_width=0,
            ),
        )
    ]

    manager_nospawn.start(config)

    left_info = manager_nospawn.c.bar["left"].info
    right_info = manager_nospawn.c.bar["right"].info

    # Screen is 600px tall so:
    # -left bar should have height of 600 - 5 - 5 - 5 - 5 = 580 (margin and border)
    # -right bar should have height of 600 - 5 - 5 = 590 (margin and no border)

    assert left_info()["height"] == 580
    assert right_info()["height"] == 590

    # Bar "width" should still be the value set in the config but "size" is
    # adjusted for margin and border:
    # -left bar should have size of 12 + 5 + 5 + 5 + 5 = 32 (margin and border)
    # -right bar should have size of 12 + 5 + 5 = 22 (margin and border)

    assert left_info()["width"] == 12
    assert left_info()["size"] == 32
    assert right_info()["width"] == 12
    assert right_info()["size"] == 22

    # Test widget offsets
    # Where there is a border, widget should be offset by that amount

    _, xoffset = manager_nospawn.c.bar["left"].eval("self.widgets[0].offsetx")
    assert xoffset == "5"

    _, yoffset = manager_nospawn.c.bar["left"].eval("self.widgets[0].offsety")
    assert xoffset == "5"

    # Where there is no border, this should be 0
    _, xoffset = manager_nospawn.c.bar["right"].eval("self.widgets[0].offsetx")
    assert xoffset == "0"

    _, yoffset = manager_nospawn.c.bar["right"].eval("self.widgets[0].offsety")
    assert xoffset == "0"
