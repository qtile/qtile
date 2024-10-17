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

import pytest

import libqtile.bar
import libqtile.config
import libqtile.confreader
import libqtile.layout
from libqtile import widget

sep = widget.Sep()

parameters = [
    (libqtile.config.Screen(top=libqtile.bar.Bar([sep], 10)), "top", "width"),
    (libqtile.config.Screen(left=libqtile.bar.Bar([sep], 10)), "left", "height"),
]


@pytest.mark.parametrize("screen,location,attribute", parameters)
def test_orientations(manager_nospawn, minimal_conf_noscreen, screen, location, attribute):
    config = minimal_conf_noscreen
    config.screens = [screen]

    manager_nospawn.start(config)
    bar = manager_nospawn.c.bar[location]

    w = bar.info()["widgets"][0]
    assert w[attribute] == 3


def test_padding_and_width(manager_nospawn, minimal_conf_noscreen):
    sep = widget.Sep(padding=5, linewidth=7)

    config = minimal_conf_noscreen
    config.screens = [libqtile.config.Screen(top=libqtile.bar.Bar([sep], 10))]

    manager_nospawn.start(config)
    topbar = manager_nospawn.c.bar["top"]

    w = topbar.info()["widgets"][0]
    assert w["width"] == 12


def test_deprecated_config():
    sep = widget.Sep(height_percent=80)
    assert sep.size_percent == 80
