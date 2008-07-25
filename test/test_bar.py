import libpry, time
import libqtile, libqtile.config
import utils

class GBConfig(libqtile.config.Config):
    groups = ["a", "b", "c", "d"]
    layouts = [libqtile.layout.Max()]
    screens = [
        libqtile.Screen(
            bottom=libqtile.bar.Bar(
                        [
                            libqtile.bar.GroupBox(),
                        ],
                        20
                    ),
        )
    ]


class uGroupBox(utils.QTileTests):
    config = GBConfig()
    def test_one(self):
        time.sleep(1)
    

class GeomConf(libqtile.config.Config):
    groups = ["a", "b", "c", "d"]
    layouts = [libqtile.layout.Max()]
    screens = [
        libqtile.Screen(
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
        assert geom["width"] == 780
        assert geom["height"] == 580

        internal = self.c.internal()
        assert len(internal) == 2
        assert self.c.inspect(int(internal[0]["id"], 16))


class ErrConf(GeomConf):
    screens = [
        libqtile.Screen(left=libqtile.bar.Bar([], 10))
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
        libqtile.Screen(
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
            libqtile.Screen(
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
        i = self.c.barinfo()["bottom"]
        assert i[0]["offset"] == 0
        assert i[1]["offset"] == 10
        assert i[1]["width"] == 780
        assert i[2]["offset"] == 790

    def test_singlespacer(self):
        self.conf.screens = [
            libqtile.Screen(
                bottom=libqtile.bar.Bar(
                    [
                        libqtile.bar.Spacer(),
                    ],
                    10
                )
            )
        ]
        self.startQtile(self.conf)
        i = self.c.barinfo()["bottom"]
        assert i[0]["offset"] == 0
        assert i[0]["width"] == 800

    def test_nospacer(self):
        self.conf.screens = [
            libqtile.Screen(
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
        i = self.c.barinfo()["bottom"]
        assert i[0]["offset"] == 0
        assert i[1]["offset"] == 10


tests = [
    utils.XNest(xinerama=False), [
        uBarGeometry(),
        uGroupBox(),
        uBarErr(),
        uOffsetCalculation()
    ]
]
