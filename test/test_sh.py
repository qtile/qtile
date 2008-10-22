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

    def test_columnize(self):
        assert self.sh.columnize(["one", "two"]) == "one  two\n"
        
        self.sh.fd = cStringIO.StringIO()
        self.sh.termwidth = 1
        assert self.sh.columnize(["one", "two"]) == "one\ntwo\n"

        self.sh.fd = cStringIO.StringIO()
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


    def _call(self, cmd, args):
        v = self.sh._call(cmd, args)
        t = self.sh.fd.getvalue()
        self.sh.fd = cStringIO.StringIO()
        return v, t

    def test_call(self):
        assert self._call("status", []) == ("OK", "")
        
        v, t = self._call("nonexistent", "")
        assert "No such command" in t

        v, t = self._call("status", "(((")
        assert "Syntax error" in t

        v, t = self._call("status", "(1)")
        assert "Command exception" in t


tests = [
    utils.XNest(xinerama=True), [
        uQSh(),
    ],
]
