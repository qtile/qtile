import libqtile
import libqtile.sh
import libqtile.confreader
import libqtile.layout
import libqtile.manager
from utils import Xephyr


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
    floating_layout = libqtile.layout.floating.Floating()
    screens = [
        libqtile.manager.Screen()
    ]


@Xephyr(True, ShConfig())
def test_columnize(self):
    self.sh = libqtile.sh.QSh(self.c)
    assert self.sh.columnize(["one", "two"]) == "one  two"

    self.sh.termwidth = 1
    assert self.sh.columnize(["one", "two"]) == "one\ntwo"

    self.sh.termwidth = 15
    v = self.sh.columnize(["one", "two", "three", "four", "five"])
    assert v == 'one    two  \nthree  four \nfive '


@Xephyr(True, ShConfig())
def test_ls(self):
    self.sh = libqtile.sh.QSh(self.c)
    self.sh.do_cd("layout")
    self.sh.do_ls("")


@Xephyr(True, ShConfig())
def test_findNode(self):
    self.sh = libqtile.sh.QSh(self.c)
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


@Xephyr(True, ShConfig())
def test_do_cd(self):
    self.sh = libqtile.sh.QSh(self.c)
    assert not self.sh.do_cd("layout")
    assert self.sh.do_cd("0/wibble")
    assert not self.sh.do_cd("0/")


@Xephyr(True, ShConfig())
def test_call(self):
    self.sh = libqtile.sh.QSh(self.c)
    assert self.sh._call("status", []) == "OK"

    v = self.sh._call("nonexistent", "")
    assert "No such command" in v

    v = self.sh._call("status", "(((")
    assert "Syntax error" in v

    v = self.sh._call("status", "(1)")
    assert "Command exception" in v


@Xephyr(True, ShConfig())
def test_complete(self):
    self.sh = libqtile.sh.QSh(self.c)
    assert self.sh._complete("c", "c", 0) == "cd"
    assert self.sh._complete("c", "c", 1) == "commands"
    assert self.sh._complete("c", "c", 2) == "critical"
    assert self.sh._complete("c", "c", 3) is None

    assert self.sh._complete("cd l", "l", 0) == "layout"
    assert self.sh._complete("cd layout/", "layout/", 0) == "layout/group"
    assert self.sh._complete("cd layout/", "layout/g", 0) == "layout/group"


@Xephyr(True, ShConfig())
def test_help(self):
    self.sh = libqtile.sh.QSh(self.c)
    assert self.sh.do_help("nonexistent").startswith("No such command")
    assert self.sh.do_help("help")
