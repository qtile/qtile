import time
import libpry
import libqtile, libqtile.config
import utils

class MaxAll(libqtile.config.Config):
    groups = ["a", "b", "c", "d"]
    layouts = [libqtile.layout.Max()]
    screens = [
        libqtile.Screen(
            left=libqtile.bar.Bar([], 10),
            right=libqtile.bar.Bar([], 10),
            top=libqtile.bar.Bar([], 10),
            bottom=libqtile.bar.Bar([], 10),
        )
    ]


class uBarGeometry(utils.QTileTests):
    config = MaxAll()
    def test_geometry(self):
        self.testWindow("one")
        g = self.c.screens()[0]["gaps"]
        assert g["top"] == (0, 0, 800, 10)
        assert g["bottom"] == (0, 590, 800, 10)
        assert g["left"] == (0, 10, 10, 580)
        assert g["right"] == (790, 10, 10, 580)
        assert len(self.c.windows()) == 1


tests = [
    utils.XNest(xinerama=False), [
        uBarGeometry()
    ]
]
