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

import pytest
import six

import libqtile.layout
import libqtile.bar
import libqtile.widget
import libqtile.manager
import libqtile.config
import libqtile.confreader


class GBConfig(object):
    auto_fullscreen = True
    keys = []
    mouse = []
    groups = [
        libqtile.config.Group("a"),
        libqtile.config.Group("bb"),
        libqtile.config.Group("ccc"),
        libqtile.config.Group("dddd"),
        libqtile.config.Group("Pppy")
    ]
    layouts = [libqtile.layout.stack.Stack(num_stacks=1)]
    floating_layout = libqtile.layout.floating.Floating()
    screens = [
        libqtile.config.Screen(
            top=libqtile.bar.Bar(
                [
                    libqtile.widget.CPUGraph(
                        width=libqtile.bar.STRETCH,
                        type="linefill",
                        border_width=20,
                        margin_x=1,
                        margin_y=1
                    ),
                    libqtile.widget.MemoryGraph(type="line"),
                    libqtile.widget.SwapGraph(type="box"),
                    libqtile.widget.TextBox(name="text",
                                            background="333333"),
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
                50
            ),
            # TODO: Add vertical bars and test widgets that support them
        )
    ]
    main = None


gb_config = pytest.mark.parametrize("qtile", [GBConfig], indirect=True)


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
    assert c.complete("~") != "~"

    c.reset()
    s = "thisisatotallynonexistantpathforsure"
    assert c.complete(s) == s
    assert c.actual() == s
    c.reset()


@gb_config
def test_draw(qtile):
    qtile.test_window("one")
    b = qtile.c.bar["bottom"].info()
    assert b["widgets"][0]["name"] == "groupbox"


@gb_config
def test_prompt(qtile):
    assert qtile.c.widget["prompt"].info()["width"] == 0
    qtile.c.spawncmd(":")
    qtile.c.widget["prompt"].fake_keypress("a")
    qtile.c.widget["prompt"].fake_keypress("Tab")

    qtile.c.spawncmd(":")
    qtile.c.widget["prompt"].fake_keypress("slash")
    qtile.c.widget["prompt"].fake_keypress("Tab")


@gb_config
def test_event(qtile):
    qtile.c.group["bb"].toscreen()


@gb_config
def test_textbox(qtile):
    assert "text" in qtile.c.list_widgets()
    s = "some text"
    qtile.c.widget["text"].update(s)
    assert qtile.c.widget["text"].get() == s
    s = "Aye, much longer string than the initial one"
    qtile.c.widget["text"].update(s)
    assert qtile.c.widget["text"].get() == s
    qtile.c.group["Pppy"].toscreen()
    qtile.c.widget["text"].set_font(fontsize=12)


@gb_config
def test_textbox_errors(qtile):
    qtile.c.widget["text"].update(None)
    qtile.c.widget["text"].update("".join(chr(i) for i in range(255)))
    qtile.c.widget["text"].update("V\xE2r\xE2na\xE7\xEE")
    qtile.c.widget["text"].update(six.u("\ua000"))


@gb_config
def test_groupbox_button_press(qtile):
    qtile.c.group["ccc"].toscreen()
    assert qtile.c.groups()["a"]["screen"] is None
    qtile.c.bar["bottom"].fake_button_press(0, "bottom", 10, 10, 1)
    assert qtile.c.groups()["a"]["screen"] == 0


class GeomConf(object):
    auto_fullscreen = False
    main = None
    keys = []
    mouse = []
    groups = [
        libqtile.config.Group("a"),
        libqtile.config.Group("b"),
        libqtile.config.Group("c"),
        libqtile.config.Group("d")
    ]
    layouts = [libqtile.layout.stack.Stack(num_stacks=1)]
    floating_layout = libqtile.layout.floating.Floating()
    screens = [
        libqtile.config.Screen(
            top=libqtile.bar.Bar([], 10),
            bottom=libqtile.bar.Bar([], 10),
            left=libqtile.bar.Bar([], 10),
            right=libqtile.bar.Bar([], 10),
        )
    ]


geom_config = pytest.mark.parametrize("qtile", [GeomConf], indirect=True)


class DBarH(libqtile.bar.Bar):
    def __init__(self, widgets, size):
        libqtile.bar.Bar.__init__(self, widgets, size)
        self.horizontal = True


class DBarV(libqtile.bar.Bar):
    def __init__(self, widgets, size):
        libqtile.bar.Bar.__init__(self, widgets, size)
        self.horizontal = False


class DWidget(object):
    def __init__(self, length, length_type):
        self.length, self.length_type = length, length_type


@geom_config
def test_geometry(qtile):
    qtile.testXeyes()
    g = qtile.c.screens()[0]["gaps"]
    assert g["top"] == (0, 0, 800, 10)
    assert g["bottom"] == (0, 590, 800, 10)
    assert g["left"] == (0, 10, 10, 580)
    assert g["right"] == (790, 10, 10, 580)
    assert len(qtile.c.windows()) == 1
    geom = qtile.c.windows()[0]
    assert geom["x"] == 10
    assert geom["y"] == 10
    assert geom["width"] == 778
    assert geom["height"] == 578
    internal = qtile.c.internal_windows()
    assert len(internal) == 4
    wid = qtile.c.bar["bottom"].info()["window"]
    assert qtile.c.window[wid].inspect()


@geom_config
def test_resize(qtile):
    def wd(l):
        return [i.length for i in l]

    def offx(l):
        return [i.offsetx for i in l]

    def offy(l):
        return [i.offsety for i in l]

    for DBar, off in ((DBarH, offx), (DBarV, offy)):
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
        assert wd(dwidget_list) == [10, 40, 41, 10]
        assert off(dwidget_list) == [0, 10, 50, 91]

        dwidget_list = [
            DWidget(10, libqtile.bar.CALCULATED)
        ]
        b._resize(100, dwidget_list)
        assert wd(dwidget_list) == [10]
        assert off(dwidget_list) == [0]

        dwidget_list = [
            DWidget(10, libqtile.bar.CALCULATED),
            DWidget(None, libqtile.bar.STRETCH)
        ]
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


class IncompatibleWidgetConf(object):
    main = None
    keys = []
    mouse = []
    groups = [libqtile.config.Group("a")]
    layouts = [libqtile.layout.stack.Stack(num_stacks=1)]
    floating_layout = libqtile.layout.floating.Floating()
    screens = [
        libqtile.config.Screen(
            left=libqtile.bar.Bar(
                [
                    # This widget doesn't support vertical orientation
                    ExampleWidget(),
                ],
                10
            ),
        )
    ]


def test_incompatible_widget(qtile_nospawn):
    config = IncompatibleWidgetConf

    # Ensure that adding a widget that doesn't support the orientation of the
    # bar raises ConfigError
    with pytest.raises(libqtile.confreader.ConfigError):
        qtile_nospawn.create_manager(config)


class MultiStretchConf(object):
    main = None
    keys = []
    mouse = []
    groups = [libqtile.config.Group("a")]
    layouts = [libqtile.layout.stack.Stack(num_stacks=1)]
    floating_layout = libqtile.layout.floating.Floating()
    screens = [
        libqtile.config.Screen(
            top=libqtile.bar.Bar(
                [
                    libqtile.widget.Spacer(libqtile.bar.STRETCH),
                    libqtile.widget.Spacer(libqtile.bar.STRETCH),
                ],
                10
            ),
        )
    ]


def test_multiple_stretches(qtile_nospawn):
    config = MultiStretchConf

    # Ensure that adding two STRETCH widgets to the same bar raises ConfigError
    with pytest.raises(libqtile.confreader.ConfigError):
        qtile_nospawn.create_manager(config)


def test_basic(qtile_nospawn):
    config = GeomConf
    config.screens = [
        libqtile.config.Screen(
            bottom=libqtile.bar.Bar(
                [
                    ExampleWidget(),
                    libqtile.widget.Spacer(libqtile.bar.STRETCH),
                    ExampleWidget()
                ],
                10
            )
        )
    ]

    qtile_nospawn.start(config)

    i = qtile_nospawn.c.bar["bottom"].info()
    assert i["widgets"][0]["offset"] == 0
    assert i["widgets"][1]["offset"] == 10
    assert i["widgets"][1]["width"] == 780
    assert i["widgets"][2]["offset"] == 790
    libqtile.hook.clear()


def test_singlespacer(qtile_nospawn):
    config = GeomConf
    config.screens = [
        libqtile.config.Screen(
            bottom=libqtile.bar.Bar(
                [
                    libqtile.widget.Spacer(libqtile.bar.STRETCH),
                ],
                10
            )
        )
    ]

    qtile_nospawn.start(config)

    i = qtile_nospawn.c.bar["bottom"].info()
    assert i["widgets"][0]["offset"] == 0
    assert i["widgets"][0]["width"] == 800
    libqtile.hook.clear()


def test_nospacer(qtile_nospawn):
    config = GeomConf
    config.screens = [
        libqtile.config.Screen(
            bottom=libqtile.bar.Bar(
                [
                    ExampleWidget(),
                    ExampleWidget()
                ],
                10
            )
        )
    ]

    qtile_nospawn.start(config)

    i = qtile_nospawn.c.bar["bottom"].info()
    assert i["widgets"][0]["offset"] == 0
    assert i["widgets"][1]["offset"] == 10
    libqtile.hook.clear()
