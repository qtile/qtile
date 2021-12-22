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

from libqtile import config, ipc, resources
from libqtile.command.interface import IPCCommandInterface
from libqtile.confreader import Config
from libqtile.layout import Max
from libqtile.sh import QSh


class ShConfig(Config):
    keys = []
    mouse = []
    groups = [
        config.Group("a"),
        config.Group("b"),
    ]
    layouts = [
        Max(),
    ]
    floating_layout = resources.default_config.floating_layout
    screens = [config.Screen()]


sh_config = pytest.mark.parametrize("manager", [ShConfig], indirect=True)


@sh_config
def test_columnize(manager):
    client = ipc.Client(manager.sockfile)
    command = IPCCommandInterface(client)
    sh = QSh(command)
    assert sh.columnize(["one", "two"]) == "one  two"

    sh.termwidth = 1
    assert sh.columnize(["one", "two"], update_termwidth=False) == "one\ntwo"

    sh.termwidth = 15
    v = sh.columnize(["one", "two", "three", "four", "five"], update_termwidth=False)
    assert v == "one    two  \nthree  four \nfive "


@sh_config
def test_ls(manager):
    client = ipc.Client(manager.sockfile)
    command = IPCCommandInterface(client)
    sh = QSh(command)
    assert sh.do_ls(None) == "bar/     group/   layout/  screen/  widget/  window/  core/  "
    assert sh.do_ls("") == "bar/     group/   layout/  screen/  widget/  window/  core/  "
    assert sh.do_ls("layout") == "layout/group/   layout/window/  layout/screen/  layout[0]/    "

    assert sh.do_cd("layout") == "layout"
    assert sh.do_ls(None) == "group/   window/  screen/"
    assert (
        sh.do_ls("screen")
        == "screen/layout/  screen/window/  screen/bar/     screen/widget/  screen/group/ "
    )


@sh_config
def test_do_cd(manager):
    client = ipc.Client(manager.sockfile)
    command = IPCCommandInterface(client)
    sh = QSh(command)
    assert sh.do_cd("layout") == "layout"
    assert sh.do_cd("../layout/0") == "layout[0]"
    assert sh.do_cd("..") == "/"
    assert sh.do_cd("layout") == "layout"
    assert sh.do_cd("../layout0/wibble") == "No such path."
    assert sh.do_cd(None) == "/"


@sh_config
def test_call(manager):
    client = ipc.Client(manager.sockfile)
    command = IPCCommandInterface(client)
    sh = QSh(command)
    assert sh.process_line("status()") == "OK"

    v = sh.process_line("nonexistent()")
    assert v == "Command does not exist: nonexistent"

    v = sh.process_line("status(((")
    assert v == "Invalid command: status((("

    v = sh.process_line("status(1)")
    assert v.startswith("Caught command exception")


@sh_config
def test_complete(manager):
    client = ipc.Client(manager.sockfile)
    command = IPCCommandInterface(client)
    sh = QSh(command)
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
def test_help(manager):
    client = ipc.Client(manager.sockfile)
    command = IPCCommandInterface(client)
    sh = QSh(command)
    assert sh.do_help("nonexistent").startswith("No such command")
    assert sh.do_help("help")
