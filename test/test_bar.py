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

import pytest

import libqtile.bar
import libqtile.config
import libqtile.confreader
import libqtile.layout
import libqtile.widget


class GBConfig(libqtile.confreader.Config):
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


gb_config = pytest.mark.parametrize("self", [GBConfig], indirect=True)


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
    with tempfile.TemporaryDirectory(prefix="qtile_test_",
                                     dir=home_dir) as absolute_tmp_path:
        tmp_dirname = absolute_tmp_path[len(home_dir + os.sep):]
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
def test_draw(self):
    self.test_window("one")
    b = self.c.bar["bottom"].info()
    assert b["widgets"][0]["name"] == "groupbox"


@gb_config
def test_prompt(self):
    assert self.c.widget["prompt"].info()["width"] == 0
    self.c.spawncmd(":")
    self.c.widget["prompt"].fake_keypress("a")
    self.c.widget["prompt"].fake_keypress("Tab")

    self.c.spawncmd(":")
    self.c.widget["prompt"].fake_keypress("slash")
    self.c.widget["prompt"].fake_keypress("Tab")


@gb_config
def test_event(self):
    self.c.group["bb"].toscreen()


@gb_config
def test_textbox(self):
    assert "text" in self.c.list_widgets()
    s = "some text"
    self.c.widget["text"].update(s)
    assert self.c.widget["text"].get() == s
    s = "Aye, much longer string than the initial one"
    self.c.widget["text"].update(s)
    assert self.c.widget["text"].get() == s
    self.c.group["Pppy"].toscreen()
    self.c.widget["text"].set_font(fontsize=12)


@gb_config
def test_textbox_errors(self):
    self.c.widget["text"].update(None)
    self.c.widget["text"].update("".join(chr(i) for i in range(255)))
    self.c.widget["text"].update("V\xE2r\xE2na\xE7\xEE")
    self.c.widget["text"].update("\ua000")


@gb_config
def test_groupbox_button_press(self):
    self.c.group["ccc"].toscreen()
    assert self.c.groups()["a"]["screen"] is None
    self.c.bar["bottom"].fake_button_press(0, "bottom", 10, 10, 1)
    assert self.c.groups()["a"]["screen"] == 0


class GeomConf(libqtile.confreader.Config):
    auto_fullscreen = False
    keys = []
    mouse = []
    groups = [
        libqtile.config.Group("a"),
        libqtile.config.Group("b"),
        libqtile.config.Group("c"),
        libqtile.config.Group("d")
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


geom_config = pytest.mark.parametrize("self", [GeomConf], indirect=True)


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
def test_geometry(self):
    self.test_xeyes()
    g = self.c.screens()[0]["gaps"]
    assert g["top"] == (0, 0, 800, 10)
    assert g["bottom"] == (0, 590, 800, 10)
    assert g["left"] == (0, 10, 10, 580)
    assert g["right"] == (790, 10, 10, 580)
    assert len(self.c.windows()) == 1
    geom = self.c.windows()[0]
    assert geom["x"] == 10
    assert geom["y"] == 10
    assert geom["width"] == 778
    assert geom["height"] == 578
    internal = self.c.internal_windows()
    assert len(internal) == 4
    wid = self.c.bar["bottom"].info()["window"]
    assert self.c.window[wid].inspect()


@geom_config
def test_resize(self):
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


class IncompatibleWidgetConf(libqtile.confreader.Config):
    keys = []
    mouse = []
    groups = [libqtile.config.Group("a")]
    layouts = [libqtile.layout.stack.Stack(num_stacks=1)]
    floating_layout = libqtile.resources.default_config.floating_layout
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


def test_incompatible_widget(self_nospawn):
    config = IncompatibleWidgetConf

    # Ensure that adding a widget that doesn't support the orientation of the
    # bar raises ConfigError
    with pytest.raises(libqtile.confreader.ConfigError):
        self_nospawn.create_manager(config)


def test_basic(self_nospawn):
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
                    ExampleWidget()
                ],
                10
            )
        )
    ]

    self_nospawn.start(config)

    i = self_nospawn.c.bar["bottom"].info()
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


def test_singlespacer(self_nospawn):
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

    self_nospawn.start(config)

    i = self_nospawn.c.bar["bottom"].info()
    assert i["widgets"][0]["offset"] == 0
    assert i["widgets"][0]["width"] == 800
    libqtile.hook.clear()


def test_nospacer(self_nospawn):
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

    self_nospawn.start(config)

    i = self_nospawn.c.bar["bottom"].info()
    assert i["widgets"][0]["offset"] == 0
    assert i["widgets"][1]["offset"] == 10
    libqtile.hook.clear()
