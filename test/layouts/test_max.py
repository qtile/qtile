# Copyright (c) 2011 Florian Mounier
# Copyright (c) 2012, 2014-2015 Tycho Andersen
# Copyright (c) 2013 Mattias Svala
# Copyright (c) 2013 Craig Barnes
# Copyright (c) 2014 ramnes
# Copyright (c) 2014 Sean Vig
# Copyright (c) 2014 Adi Sieker
# Copyright (c) 2014 Chris Wesseling
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

from libqtile import layout
import libqtile.manager
import libqtile.config
from ..conftest import no_xinerama


class MaxConfig:
    auto_fullscreen = True
    main = None
    groups = [
        libqtile.config.Group("a"),
        libqtile.config.Group("b"),
        libqtile.config.Group("c"),
        libqtile.config.Group("d")
    ]
    layouts = [
        layout.Max()
    ]
    floating_layout = libqtile.layout.floating.Floating()
    keys = []
    mouse = []
    screens = []


max_config = lambda x: \
    no_xinerama(pytest.mark.parametrize("qtile", [MaxConfig], indirect=True)(x))


@max_config
def test_max_simple(qtile):
    qtile.testWindow("one")
    assert qtile.c.layout.info()["clients"] == ["one"]
    qtile.testWindow("two")
    assert qtile.c.layout.info()["clients"] == ["one", "two"]


@max_config
def test_max_updown(qtile):
    qtile.testWindow("one")
    qtile.testWindow("two")
    qtile.testWindow("three")
    assert qtile.c.layout.info()["clients"] == ["one", "two", "three"]
    qtile.c.layout.up()
    assert qtile.c.groups()["a"]["focus"] == "two"
    qtile.c.layout.down()
    assert qtile.c.groups()["a"]["focus"] == "three"


@max_config
def test_max_remove(qtile):
    qtile.testWindow("one")
    two = qtile.testWindow("two")
    assert qtile.c.layout.info()["clients"] == ["one", "two"]
    qtile.kill_window(two)
    assert qtile.c.layout.info()["clients"] == ["one"]


@max_config
def test_closing_dialog(qtile):
    # Closing a floating window that has focus must return the focus to the
    # window that was previously focused

    # Start by testing a dialog that is the first open window in the group
    dialog1 = qtile.testWindow("dialog1")
    qtile.testWindow("one")
    qtile.testWindow("two")
    three = qtile.testWindow("three")
    qtile.c.layout.down()
    assert qtile.c.window.info()['name'] == "dialog1", qtile.c.window.info()['name']
    qtile.c.window.toggle_floating()
    qtile.kill_window(dialog1)
    assert qtile.c.window.info()['name'] == "three", qtile.c.window.info()['name']

    # Now test a dialog that is the last open window in the group
    dialog2 = qtile.testWindow("dialog2")
    qtile.c.window.toggle_floating()
    qtile.kill_window(dialog2)
    assert qtile.c.window.info()['name'] == "three", qtile.c.window.info()['name']

    # Now test a dialog that is neither the first nor the last open window in
    # the group
    dialog3 = qtile.testWindow("dialog3")
    four = qtile.testWindow("four")
    qtile.testWindow("five")
    qtile.testWindow("six")
    # TODO: for a more generic test, find a way to focus 'five', then focus
    #  'dialog3' skipping 'four', so that then, after closing 'dialog3', the
    #  focus must be returned to 'five', which better represents a generic
    #  window that wasn't necessarily opened immediately after the dialog
    qtile.c.layout.up()
    qtile.c.layout.up()
    qtile.c.layout.up()
    assert qtile.c.window.info()['name'] == "dialog3", qtile.c.window.info()['name']
    qtile.c.window.toggle_floating()
    qtile.kill_window(dialog3)
    assert qtile.c.window.info()['name'] == "four", qtile.c.window.info()['name']

    # Finally test a case in which the window that had focus previously is
    # closed without stealing focus from the dialog, thus requiring to find the
    # window that had focus even before that (this tests the history of focus)
    dialog4 = qtile.testWindow("dialog4")
    qtile.c.layout.up()
    qtile.c.layout.up()
    qtile.c.layout.up()
    assert qtile.c.window.info()['name'] == "two", qtile.c.window.info()['name']
    qtile.c.layout.down()
    qtile.c.layout.down()
    qtile.c.layout.down()
    assert qtile.c.window.info()['name'] == "dialog4", qtile.c.window.info()['name']
    qtile.c.window.toggle_floating()
    qtile.kill_window(three)
    qtile.kill_window(four)
    qtile.kill_window(dialog4)
    assert qtile.c.window.info()['name'] == "two", qtile.c.window.info()['name']


@max_config
def test_closing_notification(qtile):
    # Closing a floating window that doesn't have focus must not change the
    # currently focused window

    # TODO: for more proper testing, the notification windows should be created
    # without giving them focus

    # Start by testing a notification that is the first open window in the
    # group
    notification1 = qtile.testWindow("notification1")
    qtile.c.window.toggle_floating()
    qtile.testWindow("one")
    qtile.testWindow("two")
    qtile.testWindow("three")
    qtile.c.layout.up()
    assert qtile.c.window.info()['name'] == "two", qtile.c.window.info()['name']
    qtile.kill_window(notification1)
    assert qtile.c.window.info()['name'] == "two", qtile.c.window.info()['name']

    # Now test a notification that is the last open window in the group
    qtile.c.layout.down()
    notification2 = qtile.testWindow("notification2")
    qtile.c.window.toggle_floating()
    # Create and kill 'temp', otherwise qtile.c.layout.up() won't work
    temp = qtile.testWindow("temp")
    qtile.c.layout.up()
    qtile.c.layout.up()
    qtile.kill_window(temp)
    assert qtile.c.window.info()['name'] == "two", qtile.c.window.info()['name']
    qtile.kill_window(notification2)
    assert qtile.c.window.info()['name'] == "two", qtile.c.window.info()['name']

    # Now test a notification that is neither the first nor the last open
    # window in the group
    qtile.c.layout.down()
    notification3 = qtile.testWindow("notification3")
    qtile.c.window.toggle_floating()
    four = qtile.testWindow("four")
    five = qtile.testWindow("five")
    qtile.c.layout.up()
    qtile.c.layout.up()
    qtile.c.layout.up()
    assert qtile.c.window.info()['name'] == "two", qtile.c.window.info()['name']
    qtile.kill_window(notification3)
    assert qtile.c.window.info()['name'] == "two", qtile.c.window.info()['name']
