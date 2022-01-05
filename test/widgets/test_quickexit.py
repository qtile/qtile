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
from libqtile.ipc import IPCError


def test_trigger_and_cancel(manager_nospawn, minimal_conf_noscreen):

    # Set a long interval to allow for unanticipated delays in testing environment
    qewidget = widget.QuickExit(timer_interval=100)

    config = minimal_conf_noscreen
    config.screens = [libqtile.config.Screen(top=libqtile.bar.Bar([qewidget], 10))]

    manager_nospawn.start(config)
    topbar = manager_nospawn.c.bar["top"]

    # Default text
    w = topbar.info()["widgets"][0]
    assert w["text"] == "[ shutdown ]"

    # Click widget to start countdown
    topbar.fake_button_press(0, "top", 0, 0, button=1)
    w = topbar.info()["widgets"][0]
    assert w["text"] == "[ 4 seconds ]"

    # Click widget again to cancel countdown
    topbar.fake_button_press(0, "top", 0, 0, button=1)
    w = topbar.info()["widgets"][0]
    assert w["text"] == "[ shutdown ]"


def test_exit(manager_nospawn, minimal_conf_noscreen):

    # Set a short interval and start so widget exits immediately
    qewidget = widget.QuickExit(timer_interval=0.001, countdown_start=1)

    config = minimal_conf_noscreen
    config.screens = [libqtile.config.Screen(top=libqtile.bar.Bar([qewidget], 10))]

    manager_nospawn.start(config)
    topbar = manager_nospawn.c.bar["top"]

    # Click widget to start countdown
    topbar.fake_button_press(0, "top", 0, 0, button=1)

    # Trying to access bar should now give IPCError or a ConnectionResetError
    # as qtile has shutdown
    with pytest.raises((IPCError, ConnectionResetError)):
        assert topbar.info()
