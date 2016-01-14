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

from libqtile import layout
import libqtile.manager
import libqtile.config
from ..utils import Xephyr


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


@Xephyr(False, MaxConfig())
def test_max_simple(self):
    self.testWindow("one")
    assert self.c.layout.info()["clients"] == ["one"]
    self.testWindow("two")
    assert self.c.layout.info()["clients"] == ["one", "two"]


@Xephyr(False, MaxConfig())
def test_max_updown(self):
    self.testWindow("one")
    self.testWindow("two")
    self.testWindow("three")
    assert self.c.layout.info()["clients"] == ["one", "two", "three"]
    self.c.layout.up()
    assert self.c.groups()["a"]["focus"] == "two"
    self.c.layout.down()
    assert self.c.groups()["a"]["focus"] == "three"


@Xephyr(False, MaxConfig())
def test_max_remove(self):
    self.testWindow("one")
    two = self.testWindow("two")
    assert self.c.layout.info()["clients"] == ["one", "two"]
    self.kill(two)
    assert self.c.layout.info()["clients"] == ["one"]


@Xephyr(False, MaxConfig())
def test_closing_dialog(self):
    # Closing a floating window that has focus must return the focus to the
    # window that was previously focused

    # Start by testing a dialog that is the first open window in the group
    dialog1 = self.testWindow("dialog1")
    self.testWindow("one")
    self.testWindow("two")
    three = self.testWindow("three")
    self.c.layout.down()
    assert self.c.window.info()['name'] == "dialog1", self.c.window.info()[
                                                                        'name']
    self.c.window.toggle_floating()
    self.kill(dialog1)
    assert self.c.window.info()['name'] == "three", self.c.window.info()[
                                                                        'name']

    # Now test a dialog that is the last open window in the group
    dialog2 = self.testWindow("dialog2")
    self.c.window.toggle_floating()
    self.kill(dialog2)
    assert self.c.window.info()['name'] == "three", self.c.window.info()[
                                                                        'name']

    # Now test a dialog that is neither the first nor the last open window in
    # the group
    dialog3 = self.testWindow("dialog3")
    four = self.testWindow("four")
    self.testWindow("five")
    self.testWindow("six")
    # TODO: for a more generic test, find a way to focus 'five', then focus
    #  'dialog3' skipping 'four', so that then, after closing 'dialog3', the
    #  focus must be returned to 'five', which better represents a generic
    #  window that wasn't necessarily opened immediately after the dialog
    self.c.layout.up()
    self.c.layout.up()
    self.c.layout.up()
    assert self.c.window.info()['name'] == "dialog3", self.c.window.info()[
                                                                        'name']
    self.c.window.toggle_floating()
    self.kill(dialog3)
    assert self.c.window.info()['name'] == "four", self.c.window.info()['name']

    # Finally test a case in which the window that had focus previously is
    # closed without stealing focus from the dialog, thus requiring to find the
    # window that had focus even before that (this tests the history of focus)
    dialog4 = self.testWindow("dialog4")
    self.c.layout.up()
    self.c.layout.up()
    self.c.layout.up()
    assert self.c.window.info()['name'] == "two", self.c.window.info()['name']
    self.c.layout.down()
    self.c.layout.down()
    self.c.layout.down()
    assert self.c.window.info()['name'] == "dialog4", self.c.window.info()[
                                                                        'name']
    self.c.window.toggle_floating()
    self.kill(three)
    self.kill(four)
    self.kill(dialog4)
    assert self.c.window.info()['name'] == "two", self.c.window.info()['name']


@Xephyr(False, MaxConfig())
def test_closing_notification(self):
    # Closing a floating window that doesn't have focus must not change the
    # currently focused window

    # TODO: for more proper testing, the notification windows should be created
    # without giving them focus

    # Start by testing a notification that is the first open window in the
    # group
    notification1 = self.testWindow("notification1")
    self.c.window.toggle_floating()
    self.testWindow("one")
    self.testWindow("two")
    self.testWindow("three")
    self.c.layout.up()
    assert self.c.window.info()['name'] == "two", self.c.window.info()['name']
    self.kill(notification1)
    assert self.c.window.info()['name'] == "two", self.c.window.info()['name']

    # Now test a notification that is the last open window in the group
    self.c.layout.down()
    notification2 = self.testWindow("notification2")
    self.c.window.toggle_floating()
    # Create and kill 'temp', otherwise self.c.layout.up() won't work
    temp = self.testWindow("temp")
    self.c.layout.up()
    self.c.layout.up()
    self.kill(temp)
    assert self.c.window.info()['name'] == "two", self.c.window.info()['name']
    self.kill(notification2)
    assert self.c.window.info()['name'] == "two", self.c.window.info()['name']

    # Now test a notification that is neither the first nor the last open
    # window in the group
    self.c.layout.down()
    notification3 = self.testWindow("notification3")
    self.c.window.toggle_floating()
    four = self.testWindow("four")
    five = self.testWindow("five")
    self.c.layout.up()
    self.c.layout.up()
    self.c.layout.up()
    assert self.c.window.info()['name'] == "two", self.c.window.info()['name']
    self.kill(notification3)
    assert self.c.window.info()['name'] == "two", self.c.window.info()['name']
