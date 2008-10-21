import cStringIO
import libpry
import libqtile, libqtile.sh
import utils

class ShConfig(libqtile.confreader.Config):
    keys = []
    groups = ["a", "b"]
    layouts = [
        libqtile.layout.Max(),
    ]
    screens = [
        libqtile.manager.Screen()
    ]

class uQSh(utils.QTileTests):
    config = ShConfig()
    def setUp(self):
        utils.QTileTests.setUp(self)
        self.sh = libqtile.sh.QSh(self.c)
        self.sh.fd = cStringIO.StringIO()

    def test_printColumns(self):
        self.sh.printColumns(["one", "two"])
        assert self.sh.fd.getvalue() == "one  two\n"
        
        self.sh.fd = cStringIO.StringIO()
        self.sh.termwidth = 1
        self.sh.printColumns(["one", "two"])
        assert self.sh.fd.getvalue() == "one\ntwo\n"

        self.sh.fd = cStringIO.StringIO()
        self.sh.termwidth = 15
        self.sh.printColumns(["one", "two", "three", "four", "five"])
        assert self.sh.fd.getvalue() == 'one    two  \nthree  four \nfive \n'

    def test_ls(self):
        self.sh.do_ls()

    def test_cd(self):
        self.sh.do_cd("layout")
        assert self.sh.current.name == "layout"
        assert self.sh.current.parent


tests = [
    utils.XNest(xinerama=True), [
        uQSh(),
    ],
]
