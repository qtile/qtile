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

space = widget.Spacer()

parameters = [
    (libqtile.config.Screen(top=libqtile.bar.Bar([space], 10)), "top", "width"),
    (libqtile.config.Screen(left=libqtile.bar.Bar([space], 10)), "left", "height"),
]


@pytest.mark.parametrize("screen,location,attribute", parameters)
def test_stretch(manager_nospawn, minimal_conf_noscreen, screen, location, attribute):
    config = minimal_conf_noscreen
    config.screens = [screen]

    manager_nospawn.start(config)
    bar = manager_nospawn.c.bar[location]

    info = bar.info()
    assert info["widgets"][0][attribute] == info[attribute]


space = widget.Spacer(length=100)
parameters = [
    (libqtile.config.Screen(top=libqtile.bar.Bar([space], 10)), "top", "width"),
    (libqtile.config.Screen(left=libqtile.bar.Bar([space], 10)), "left", "height"),
]


@pytest.mark.parametrize("screen,location,attribute", parameters)
def test_fixed_size(manager_nospawn, minimal_conf_noscreen, screen, location, attribute):
    config = minimal_conf_noscreen
    config.screens = [screen]

    manager_nospawn.start(config)
    bar = manager_nospawn.c.bar[location]

    info = bar.info()
    assert info["widgets"][0][attribute] == 100
