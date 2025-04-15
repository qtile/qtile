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
from libqtile.command.interface import CommandException
from libqtile.widget.crashme import _CrashMe


def test_crashme_init(manager_nospawn, minimal_conf_noscreen):
    crash = _CrashMe()

    config = minimal_conf_noscreen
    config.screens = [libqtile.config.Screen(top=libqtile.bar.Bar([crash], 10))]

    manager_nospawn.start(config)

    topbar = manager_nospawn.c.bar["top"]
    w = topbar.info()["widgets"][0]

    # Check that BadWidget has been replaced by ConfigErrorWidget
    assert w["name"] == "_crashme"
    assert w["text"] == "Crash me !"

    # Testing errors. Exceptions are wrapped in CommandException
    # so we catch that and match for the intended exception.

    # Left click generates ZeroDivisionError
    with pytest.raises(CommandException) as e_info:
        topbar.fake_button_press(0, 0, button=1)

    assert e_info.match("ZeroDivisionError")
