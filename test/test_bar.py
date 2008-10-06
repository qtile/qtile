import libpry, time
import libqtile, libqtile.config
import utils

class GBConfig(libqtile.config.Config):
    groups = ["a", "b", "c", "d"]
    layouts = [libqtile.layout.Stack(stacks=1, borderWidth=10)]
    screens = [
        libqtile.manager.Screen(
            bottom=libqtile.bar.Bar(
                        [
                            libqtile.bar.GroupBox(),
                            libqtile.bar.WindowName(),
                            libqtile.bar.TextBox("text", text="default", width=100),
                            libqtile.bar.MeasureBox("measure", width=100),
                        ],
                        20
                    ),
        )
    ]


class uWidgets(utils.QTileTests):
    config = GBConfig()
    def test_draw(self):
        self.testWindow("one")
        b = self.c.bar["bottom"].info()
        assert b["widgets"][0]["name"] == "GroupBox"

    def test_event(self):
        self.c.pullgroup("b")
        self.c.log()

    def test_textbox(self):
        assert "text" in self.c.list_widgets()
        self.c.widget["text"].textbox_update("testing")
        assert self.c.widget["text"].textbox_get() == "testing"

    def test_groupbox_click(self):
        self.c.pullgroup("c")
        assert self.c.groups()["a"]["screen"] == None
        self.c.bar["bottom"].bar_fake_click(0, "bottom", 10, 10)
        assert self.c.groups()["a"]["screen"] == 0

    def test_measurebox(self):
        libpry.raises("out of range", self.c.widget["measure"].measurebox_update, 200)
        libpry.raises("out of range", self.c.widget["measure"].measurebox_update, -1)
        self.c.widget["measure"].measurebox_update(0)
        self.c.widget["measure"].measurebox_update(10)
        self.c.widget["measure"].measurebox_update(30)
        self.c.widget["measure"].measurebox_update(50)
        self.c.widget["measure"].measurebox_update(80)
        self.c.widget["measure"].measurebox_update(100)
        

class GeomConf(libqtile.config.Config):
    groups = ["a", "b", "c", "d"]
    layouts = [libqtile.layout.Stack(stacks=1, borderWidth=10)]
    screens = [
        libqtile.manager.Screen(
            left=libqtile.bar.Gap(10),
            right=libqtile.bar.Gap(10),
            top=libqtile.bar.Bar([], 10),
            bottom=libqtile.bar.Bar([], 10),
        )
    ]


class uBarGeometry(utils.QTileTests):
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
        assert self.c.inspect(int(internal[0]["id"], 16))


class ErrConf(GeomConf):
    screens = [
        libqtile.manager.Screen(left=libqtile.bar.Bar([], 10))
    ]


class uBarErr(utils._QTileTruss):
    def test_err(self):
        config = ErrConf()
        self.qtileRaises("top or the bottom of the screen", config)


class TestWidget(libqtile.bar._Widget):
    def _configure(self, qtile, bar, event):
        libqtile.bar._Widget._configure(self, qtile, bar, event)
        self.width = 10

    def draw(self): pass


class OffsetConf(GeomConf):
    screens = [
        libqtile.manager.Screen(
            bottom=libqtile.bar.Bar(
                [
                    TestWidget(),
                    libqtile.bar.Spacer(),
                    TestWidget()
                ],
                10
            )
        )
    ]


class uOffsetCalculation(utils._QTileTruss):
    def setUp(self):
        utils._QTileTruss.setUp(self)
        self.conf = GeomConf()

    def tearDown(self):
        utils._QTileTruss.tearDown(self)
        self.stopQtile()

    def test_basic(self):
        self.conf.screens = [
            libqtile.manager.Screen(
                bottom=libqtile.bar.Bar(
                    [
                        TestWidget(),
                        libqtile.bar.Spacer(),
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
                        libqtile.bar.Spacer(),
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
