import libpry
import libqtile, libqtile.sh, libqtile.confreader, libqtile.layout, libqtile.manager
import utils

class ShConfig(libqtile.confreader.Config):
    keys = []
    mouse = []
    groups = [
        libqtile.manager.Group("a"),
        libqtile.manager.Group("b"),
    ]
    layouts = [
        libqtile.layout.Max(),
    ]
    screens = [
        libqtile.manager.Screen()
    ]


class uQSh(utils.QtileTests):
    config = ShConfig()
    def setUp(self):
        utils.QtileTests.setUp(self)
        self.sh = libqtile.sh.QSh(self.c)

    def test_columnize(self):
        assert self.sh.columnize(["one", "two"]) == "one  two"

        self.sh.termwidth = 1
        assert self.sh.columnize(["one", "two"]) == "one\ntwo"

        self.sh.termwidth = 15
        v = self.sh.columnize(["one", "two", "three", "four", "five"])
        assert v == 'one    two  \nthree  four \nfive '

    def test_ls(self):
        self.sh.do_cd("layout")
        self.sh.do_ls("")

    def test_findNode(self):
        n = self.sh._findNode(self.sh.current, "layout")
        assert n.path == "layout"
        assert n.parent

        n = self.sh._findNode(n, "0")
        assert n.path == "layout[0]"

        n = self.sh._findNode(n, "..")
        assert n.path == "layout"

        n = self.sh._findNode(n, "0", "..")
        assert n.path == "layout"

        n = self.sh._findNode(n, "..", "layout", 0)
        assert n.path == "layout[0]"

        assert not self.sh._findNode(n, "wibble")
        assert not self.sh._findNode(n, "..", "0", "wibble")

    def test_do_cd(self):
        assert not self.sh.do_cd("layout")
        assert self.sh.do_cd("0/wibble")
        assert not self.sh.do_cd("0/")

    def test_call(self):
        assert self.sh._call("status", []) == "OK"

        v = self.sh._call("nonexistent", "")
        assert "No such command" in v

        v = self.sh._call("status", "(((")
        assert "Syntax error" in v

        v = self.sh._call("status", "(1)")
        assert "Command exception" in v

    def test_complete(self):
        assert self.sh._complete("c", "c", 0) == "cd"
        assert self.sh._complete("c", "c", 1) == "commands"
        assert self.sh._complete("c", "c", 2) is None

        assert self.sh._complete("cd l", "l", 0) == "layout"
        assert self.sh._complete("cd layout/", "layout/", 0) == "layout/group"
        assert self.sh._complete("cd layout/", "layout/g", 0) == "layout/group"

    def test_help(self):
        assert self.sh.do_help("log")
        assert self.sh.do_help("nonexistent").startswith("No such command")
        assert self.sh.do_help("help")


tests = [
    utils.Xephyr(xinerama=True), [
        uQSh(),
    ],
]
