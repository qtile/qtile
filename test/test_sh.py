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

import pytest

from libqtile import config, command
from libqtile.layout import floating, Max
from libqtile.sh import QSh


class ShConfig:
    keys = []
    mouse = []
    groups = [
        config.Group("a"),
        config.Group("b"),
    ]
    layouts = [
        Max(),
    ]
    floating_layout = floating.Floating()
    screens = [
        config.Screen()
    ]
    main = None


sh_config = pytest.mark.parametrize("qtile", [ShConfig], indirect=True)


@sh_config
def test_columnize(qtile):
    client = command.Client(qtile.sockfile)
    sh = QSh(client)
    assert sh.columnize(["one", "two"]) == "one  two"

    sh.termwidth = 1
    assert sh.columnize(["one", "two"], update_termwidth=False) == "one\ntwo"

    sh.termwidth = 15
    v = sh.columnize(["one", "two", "three", "four", "five"], update_termwidth=False)
    assert v == 'one    two  \nthree  four \nfive '


@sh_config
def test_ls(qtile):
    client = command.Client(qtile.sockfile)
    sh = QSh(client)
    sh.do_cd("layout")
    sh.do_ls("")


@sh_config
def test_find_node(qtile):
    client = command.Client(qtile.sockfile)
    sh = QSh(client)
    n = sh._find_node(sh.current, "layout")
    assert n.path == "layout"
    assert n.parent

    n = sh._find_node(n, "0")
    assert n.path == "layout[0]"

    n = sh._find_node(n, "..")
    assert n.path == "layout"

    n = sh._find_node(n, "0", "..")
    assert n.path == "layout"

    n = sh._find_node(n, "..", "layout", 0)
    assert n.path == "layout[0]"

    assert not sh._find_node(n, "wibble")
    assert not sh._find_node(n, "..", "0", "wibble")


@sh_config
def test_do_cd(qtile):
    client = command.Client(qtile.sockfile)
    sh = QSh(client)
    assert sh.do_cd("layout") == 'layout'
    assert sh.do_cd("0/wibble") == 'No such path.'
    assert sh.do_cd("0/") == 'layout[0]'


@sh_config
def test_call(qtile):
    client = command.Client(qtile.sockfile)
    sh = QSh(client)
    assert sh._call("status", []) == "OK"

    v = sh._call("nonexistent", "")
    assert "No such command" in v

    v = sh._call("status", "(((")
    assert "Syntax error" in v

    v = sh._call("status", "(1)")
    assert "Command exception" in v


@sh_config
def test_complete(qtile):
    client = command.Client(qtile.sockfile)
    sh = QSh(client)
    assert sh._complete("c", "c") == [
        "cd",
        "commands",
        "critical",
    ]

    assert sh._complete("cd l", "l") == ["layout/"]
    assert sh._complete("cd layout/", "layout/") == [
        "layout/" + x for x in ["group", "window", "screen", "0"]
    ]
    assert sh._complete("cd layout/", "layout/g") == ["layout/group/"]


@sh_config
def test_help(qtile):
    client = command.Client(qtile.sockfile)
    sh = QSh(client)
    assert sh.do_help("nonexistent").startswith("No such command")
    assert sh.do_help("help")
