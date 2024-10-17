# Copyright (c) 2021 elParaguayo
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

# Widget specific tests

import libqtile.bar
import libqtile.config
import libqtile.confreader
import libqtile.layout
from libqtile import widget
from test.conftest import dualmonitor

ACTIVE = "#FF0000"
INACTIVE = "#00FF00"


@dualmonitor
def test_change_screen(manager_nospawn, minimal_conf_noscreen):
    cswidget = widget.CurrentScreen(active_color=ACTIVE, inactive_color=INACTIVE)

    config = minimal_conf_noscreen
    config.screens = [
        libqtile.config.Screen(top=libqtile.bar.Bar([cswidget], 10)),
        libqtile.config.Screen(),
    ]

    manager_nospawn.start(config)

    w = manager_nospawn.c.screen[0].bar["top"].info()["widgets"][0]

    assert w["text"] == "A"
    assert w["foreground"] == ACTIVE

    manager_nospawn.c.to_screen(1)

    w = manager_nospawn.c.screen[0].bar["top"].info()["widgets"][0]
    assert w["text"] == "I"
    assert w["foreground"] == INACTIVE
