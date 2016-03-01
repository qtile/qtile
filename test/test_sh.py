# Copyright (c) 2011 Florian Mounier
# Copyright (c) 2012 Tycho Andersen
# Copyright (c) 2014 Sean Vig
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import libqtile
import libqtile.sh
import libqtile.confreader
import libqtile.layout
import libqtile.manager
import libqtile.config
from .utils import Xephyr


class ShConfig(object):
    keys = []
    mouse = []
    groups = [
        libqtile.config.Group("a"),
        libqtile.config.Group("b"),
    ]
    layouts = [
        libqtile.layout.Max(),
    ]
    floating_layout = libqtile.layout.floating.Floating()
    screens = [
        libqtile.config.Screen()
    ]
    main = None


@Xephyr(True, ShConfig())
def test_columnize(self):
    self.sh = libqtile.sh.QSh(self.c)
    assert self.sh.columnize(["one", "two"]) == "one  two"

    self.sh.termwidth = 1
    assert self.sh.columnize(["one", "two"], update_termwidth=False) == "one\ntwo"

    self.sh.termwidth = 15
    v = self.sh.columnize(["one", "two", "three", "four", "five"], update_termwidth=False)
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
    assert self.sh.do_cd("layout") == 'layout'
    assert self.sh.do_cd("0/wibble") == 'No such path.'
    assert self.sh.do_cd("0/") == 'layout[0]'


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
    assert self.sh._complete("c", "c") == [
        "cd",
        "commands",
        "critical",
    ]

    assert self.sh._complete("cd l", "l") == ["layout"]
    print(self.sh._complete("cd layout/", "layout/"))
    assert self.sh._complete("cd layout/", "layout/") == [
        "layout/" + x for x in ["group", "window", "screen", "0"]
    ]
    assert self.sh._complete("cd layout/", "layout/g") == ["layout/group"]


@Xephyr(True, ShConfig())
def test_help(self):
    self.sh = libqtile.sh.QSh(self.c)
    assert self.sh.do_help("nonexistent").startswith("No such command")
    assert self.sh.do_help("help")
