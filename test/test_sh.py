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

    def test_columnize(self):
        assert self.sh.columnize(["one", "two"]) == "one  two\n"
        
        self.sh.termwidth = 1
        assert self.sh.columnize(["one", "two"]) == "one\ntwo\n"

        self.sh.termwidth = 15
        v = self.sh.columnize(["one", "two", "three", "four", "five"])
        assert v == 'one    two  \nthree  four \nfive \n'

    def test_ls(self):
        self.sh.do_cd("layout")
        self.sh.do_ls("")

    def test_cd(self):
        self.sh._cd("layout")
        assert self.sh.prompt == "layout> "
        assert self.sh.current.parent

        self.sh._cd("0")
        assert self.sh.prompt == "layout[0]> "
        self.sh.do_ls("")
        self.sh._cd("..")
        assert self.sh.prompt == "layout> "
        self.sh._cd("0", "..")
        assert self.sh.prompt == "layout> "

        assert self.sh._cd("wibble")

        self.sh.do_cd("0/wibble")
        assert self.sh.prompt == "layout> "
        self.sh.do_cd("0/")
        assert self.sh.prompt == "layout[0]> "

    def test_call(self):
        assert self.sh._call("status", []) == "OK"
        
        v = self.sh._call("nonexistent", "")
        assert "No such command" in v

        v = self.sh._call("status", "(((")
        assert "Syntax error" in v

        v = self.sh._call("status", "(1)")
        assert "Command exception" in v


tests = [
    utils.XNest(xinerama=True), [
        uQSh(),
    ],
]
