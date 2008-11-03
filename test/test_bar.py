import libpry, time
import libqtile.layout, libqtile.bar, libqtile.widget
import utils

class GBConfig:
    keys = []
    groups = ["a", "b", "c", "d"]
    layouts = [libqtile.layout.stack.Stack(stacks=1, borderWidth=10)]
    screens = [
        libqtile.manager.Screen(
            bottom=libqtile.bar.Bar(
                        [
                            libqtile.widget.GroupBox(),
                            libqtile.widget.WindowName(),
                            libqtile.widget.TextBox("text", text="default", width=100),
                            libqtile.widget.MeasureBox("measure", width=100),
                        ],
                        20
                    ),
        )
    ]


class uWidgets(utils.QtileTests):
    config = GBConfig()
    def test_draw(self):
        self.testWindow("one")
        b = self.c.bar["bottom"].info()
        assert b["widgets"][0]["name"] == "GroupBox"

    def test_event(self):
        self.c.group["b"].toscreen()
        self.c.log()

    def test_textbox(self):
        assert "text" in self.c.list_widgets()
        self.c.widget["text"].update("testing")
        assert self.c.widget["text"].get() == "testing"

    def test_groupbox_click(self):
        self.c.group["c"].toscreen()
        assert self.c.groups()["a"]["screen"] == None
        self.c.bar["bottom"].fake_click(0, "bottom", 10, 10)
        assert self.c.groups()["a"]["screen"] == 0

    def test_measurebox(self):
        libpry.raises("out of range", self.c.widget["measure"].update, 200)
        libpry.raises("out of range", self.c.widget["measure"].update, -1)
        self.c.widget["measure"].update(0)
        self.c.widget["measure"].update(10)
        self.c.widget["measure"].update(30)
        self.c.widget["measure"].update(50)
        self.c.widget["measure"].update(80)
        self.c.widget["measure"].update(100)
        

class GeomConf:
    keys = []
    groups = ["a", "b", "c", "d"]
    layouts = [libqtile.layout.stack.Stack(stacks=1, borderWidth=10)]
    screens = [
        libqtile.manager.Screen(
            left=libqtile.bar.Gap(10),
            right=libqtile.bar.Gap(10),
            top=libqtile.bar.Bar([], 10),
            bottom=libqtile.bar.Bar([], 10),
        )
    ]


class uBarGeometry(utils.QtileTests):
    config = GeomConf()
    def test_geometry(self):
        self.testWindow("one")
        g = self.c.screens()[0]["gaps"]
        assert g["top"] == (0, 0, 800, 10)
        assert g["bottom"] == (0, 590, 800, 10)
        assert g["left"] == (0, 10, 10, 580)
        assert g["right"] == (790, 10, 10, 580)
        assert len(self.c.windows()) == 1
        geom = self.c.windows()[0]
        assert geom["x"] == 10
        assert geom["y"] == 10
        assert geom["width"] == 760
        assert geom["height"] == 560

        internal = self.c.internal()
        assert len(internal) == 2

        wid = self.c.bar["bottom"].info()["window"]
        assert self.c.window[wid].inspect()


class ErrConf(GeomConf):
    screens = [
        libqtile.manager.Screen(left=libqtile.bar.Bar([], 10))
    ]


class uBarErr(utils._QtileTruss):
    def test_err(self):
        config = ErrConf()
        self.qtileRaises("top or the bottom of the screen", config)


class TestWidget(libqtile.widget.base._Widget):
    def _configure(self, qtile, bar, event):
        libqtile.widget.base._Widget._configure(self, qtile, bar, event)
        self.width = 10

    def draw(self): pass


class OffsetConf(GeomConf):
    screens = [
        libqtile.manager.Screen(
            bottom=libqtile.bar.Bar(
                [
                    TestWidget(),
                    libqtile.widget.Spacer(),
                    TestWidget()
                ],
                10
            )
        )
    ]


class uOffsetCalculation(utils._QtileTruss):
    def setUp(self):
        utils._QtileTruss.setUp(self)
        self.conf = GeomConf()

    def tearDown(self):
        utils._QtileTruss.tearDown(self)
        self.stopQtile()

    def test_basic(self):
        self.conf.screens = [
            libqtile.manager.Screen(
                bottom=libqtile.bar.Bar(
                    [
                        TestWidget(),
                        libqtile.widget.Spacer(),
                        TestWidget()
                    ],
                    10
                )
            )
        ]
        self.startQtile(self.conf)
        i = self.c.bar["bottom"].info()
        assert i["widgets"][0]["offset"] == 0
        assert i["widgets"][1]["offset"] == 10
        assert i["widgets"][1]["width"] == 780
        assert i["widgets"][2]["offset"] == 790

    def test_singlespacer(self):
        self.conf.screens = [
            libqtile.manager.Screen(
                bottom=libqtile.bar.Bar(
                    [
                        libqtile.widget.Spacer(),
                    ],
                    10
                )
            )
        ]
        self.startQtile(self.conf)
        i = self.c.bar["bottom"].info()
        assert i["widgets"][0]["offset"] == 0
        assert i["widgets"][0]["width"] == 800

    def test_nospacer(self):
        self.conf.screens = [
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
        self.startQtile(self.conf)
        i = self.c.bar["bottom"].info()
        assert i["widgets"][0]["offset"] == 0
        assert i["widgets"][1]["offset"] == 10


tests = [
    utils.XNest(xinerama=True), [
        uBarGeometry(),
        uWidgets(),
        uBarErr(),
        uOffsetCalculation()
    ]
]
