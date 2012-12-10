import time
import libqtile.layout
import libqtile.bar
import libqtile.widget
import libqtile.manager
import libqtile.dgroups
import libqtile.confreader
from utils import Xephyr


class GBConfig:
    keys = []
    mouse = []
    groups = [
        libqtile.dgroups.Group("a"),
        libqtile.dgroups.Group("bb"),
        libqtile.dgroups.Group("ccc"),
        libqtile.dgroups.Group("dddd"),
        libqtile.dgroups.Group("Pppy")
    ]
    layouts = [libqtile.layout.stack.Stack(stacks=1)]
    floating_layout = libqtile.layout.floating.Floating()
    screens = [
        libqtile.manager.Screen(
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
                        libqtile.widget.TextBox("text", background="333333"),
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
        )
    ]
    main = None


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


@Xephyr(True, GBConfig())
def test_draw(self):
    self.testWindow("one")
    b = self.c.bar["bottom"].info()
    assert b["widgets"][0]["name"] == "GroupBox"


@Xephyr(True, GBConfig())
def test_prompt(self):
    assert self.c.widget["prompt"].info()["width"] == 0
    self.c.spawncmd(":")
    self.c.widget["prompt"].fake_keypress("a")
    self.c.widget["prompt"].fake_keypress("Tab")

    self.c.spawncmd(":")
    self.c.widget["prompt"].fake_keypress("slash")
    self.c.widget["prompt"].fake_keypress("Tab")


@Xephyr(True, GBConfig())
def test_event(self):
    self.c.group["bb"].toscreen()


@Xephyr(True, GBConfig())
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
    time.sleep(3)


@Xephyr(True, GBConfig())
def test_textbox_errors(self):
    self.c.widget["text"].update(None)
    self.c.widget["text"].update("".join(chr(i) for i in range(255)))
    self.c.widget["text"].update("V\xE2r\xE2na\xE7\xEE")
    self.c.widget["text"].update(u"\ua000")


@Xephyr(True, GBConfig())
def test_groupbox_button_press(self):
    self.c.group["ccc"].toscreen()
    assert self.c.groups()["a"]["screen"] == None
    self.c.bar["bottom"].fake_button_press(0, "bottom", 10, 10, 1)
    assert self.c.groups()["a"]["screen"] == 0


class GeomConf:
    main = None
    keys = []
    mouse = []
    groups = [
        libqtile.dgroups.Group("a"),
        libqtile.dgroups.Group("b"),
        libqtile.dgroups.Group("c"),
        libqtile.dgroups.Group("d")
    ]
    layouts = [libqtile.layout.stack.Stack(stacks=1)]
    floating_layout = libqtile.layout.floating.Floating()
    screens = [
        libqtile.manager.Screen(
            left=libqtile.bar.Gap(10),
            right=libqtile.bar.Gap(10),
            top=libqtile.bar.Bar([], 10),
            bottom=libqtile.bar.Bar([], 10),
        )
    ]


class DWidget:
    def __init__(self, width, width_type):
        self.width, self.width_type = width, width_type


@Xephyr(True, GeomConf())
def test_geometry(self):
    self.testXeyes()
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
    assert len(internal) == 2
    wid = self.c.bar["bottom"].info()["window"]
    assert self.c.window[wid].inspect()


@Xephyr(True, GeomConf())
def test_resize(self):
    def wd(l):
        return [i.width for i in l]

    def off(l):
        return [i.offset for i in l]

    b = libqtile.bar.Bar([], 100)

    l = [
        DWidget(10, libqtile.bar.CALCULATED),
        DWidget(None, libqtile.bar.STRETCH),
        DWidget(None, libqtile.bar.STRETCH),
        DWidget(10, libqtile.bar.CALCULATED),
    ]
    b._resize(100, l)
    assert wd(l) == [10, 40, 40, 10]

    b._resize(101, l)
    assert wd(l) == [10, 40, 41, 10]

    l = [
        DWidget(10, libqtile.bar.CALCULATED)
    ]
    b._resize(100, l)
    assert wd(l) == [10]
    assert off(l) == [0]

    l = [
        DWidget(10, libqtile.bar.CALCULATED),
        DWidget(None, libqtile.bar.STRETCH)
    ]
    b._resize(100, l)
    assert wd(l) == [10, 90]
    assert off(l) == [0, 10]

    l = [
        DWidget(None, libqtile.bar.STRETCH),
        DWidget(10, libqtile.bar.CALCULATED),
    ]
    b._resize(100, l)
    assert wd(l) == [90, 10]
    assert off(l) == [0, 90]

    l = [
        DWidget(10, libqtile.bar.CALCULATED),
        DWidget(None, libqtile.bar.STRETCH),
        DWidget(10, libqtile.bar.CALCULATED),
    ]
    b._resize(100, l)
    assert wd(l) == [10, 80, 10]
    assert off(l) == [0, 10, 90]


class TopBottomConf(GeomConf):
    screens = [
        libqtile.manager.Screen(left=libqtile.bar.Bar([], 10))
    ]

class MultiStretchConf(GeomConf):
    screens = [
        libqtile.manager.Screen(top=libqtile.bar.Bar([
          libqtile.widget.TextBox(txt, width=libqtile.bar.STRETCH)
          for txt in ["text1", "text2"]
        ], 10))
    ]

class ErrConf:
    main = None
    keys = []
    mouse = []
    groups = [libqtile.dgroups.Group("a")]
    layouts = [libqtile.layout.stack.Stack(stacks=1)]
    floating_layout = libqtile.layout.floating.Floating()
    screens = [
        libqtile.manager.Screen(
            left=libqtile.bar.Bar([], 10),
        )
    ]


@Xephyr(True, ErrConf(), False)
def test_err(self):
    self.qtileRaises(libqtile.confreader.ConfigError, ErrConf())


class TestWidget(libqtile.widget.base._Widget):
    def __init__(self):
        libqtile.widget.base._Widget.__init__(self, 10)

    def _configure(self, qtile, bar):
        libqtile.widget.base._Widget._configure(self, qtile, bar)

    def draw(self):
        pass


@Xephyr(True, GeomConf(), False)
def test_basic(self):
    self.config.screens = [
        libqtile.manager.Screen(
            bottom=libqtile.bar.Bar(
                [
                    TestWidget(),
                    libqtile.widget.Spacer(libqtile.bar.STRETCH),
                    TestWidget()
                ],
                10
            )
        )
    ]
    self.startQtile(self.config)
    i = self.c.bar["bottom"].info()
    assert i["widgets"][0]["offset"] == 0
    assert i["widgets"][1]["offset"] == 10
    assert i["widgets"][1]["width"] == 780
    assert i["widgets"][2]["offset"] == 790
    libqtile.hook.clear()
    self.stopQtile()


@Xephyr(True, GeomConf(), False)
def test_singlespacer(self):
    self.config.screens = [
        libqtile.manager.Screen(
            bottom=libqtile.bar.Bar(
                [
                    libqtile.widget.Spacer(libqtile.bar.STRETCH),
                ],
                10
            )
        )
    ]
    self.startQtile(self.config)
    i = self.c.bar["bottom"].info()
    assert i["widgets"][0]["offset"] == 0
    assert i["widgets"][0]["width"] == 800
    libqtile.hook.clear()
    self.stopQtile()


@Xephyr(True, GeomConf(), False)
def test_nospacer(self):
    self.config.screens = [
        libqtile.manager.Screen(
            bottom=libqtile.bar.Bar(
                [
                    TestWidget(),
                    TestWidget()
                ],
                10
            )
        )
    ]
    self.startQtile(self.config)
    i = self.c.bar["bottom"].info()
    assert i["widgets"][0]["offset"] == 0
    assert i["widgets"][1]["offset"] == 10
    libqtile.hook.clear()
    self.stopQtile()
