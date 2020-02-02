# Copyright (c) 2020 Guangwang Huang
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

import libqtile.confreader
import libqtile.config
import libqtile.layout
import libqtile.bar
import libqtile.widget
from libqtile.ipc import Client
from libqtile.command_client import InteractiveCommandClient
from libqtile.command_interface import IPCCommandInterface
from libqtile.scripts.qtile_cmd import get_object, run_function


class ServerConfig:
    auto_fullscreen = True
    keys = []
    mouse = []
    groups = [
        libqtile.config.Group("a"),
        libqtile.config.Group("b"),
        libqtile.config.Group("c"),
    ]
    layouts = [
        libqtile.layout.Stack(num_stacks=1),
        libqtile.layout.Stack(num_stacks=2),
        libqtile.layout.Stack(num_stacks=3),
    ]
    floating_layout = libqtile.layout.floating.Floating()
    screens = [
        libqtile.config.Screen(
            bottom=libqtile.bar.Bar(
                [
                    libqtile.widget.TextBox(name="one"),
                ],
                20
            ),
        ),
        libqtile.config.Screen(
            bottom=libqtile.bar.Bar(
                [
                    libqtile.widget.TextBox(name="two"),
                ],
                20
            ),
        )
    ]
    main = None


server_config = pytest.mark.parametrize("qtile", [ServerConfig], indirect=True)


@server_config
def test_qtile_cmd(qtile):

    def _qtile_cmd(obj_spec, function, args):
        "Imitate the behavior of qtile_cmd"
        ipc_client = Client(qtile.sockfile)
        cmd_object = IPCCommandInterface(ipc_client)
        cmd_client = InteractiveCommandClient(cmd_object)

        obj = get_object(cmd_client, obj_spec)
        return run_function(obj, function, args)

    qtile.test_window("foo")
    wid = qtile.c.window.info()["id"]

    # e.g. qtile-cmd -o screen -f info
    for obj in ["window", "layout", "group", "screen"]:
        assert _qtile_cmd([obj], 'info', [])

    # e.g. qtile-cmd -o group a -f info
    assert _qtile_cmd(['window', wid], 'info', [])
    assert _qtile_cmd(['group', 'a'], 'info', [])
    assert _qtile_cmd(['screen', 0], 'info', [])
    assert _qtile_cmd(['bar', 'bottom'], 'info', [])

