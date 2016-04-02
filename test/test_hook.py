# Copyright (c) 2009 Aldo Cortesi
# Copyright (c) 2011 Florian Mounier
# Copyright (c) 2011 Anshuman Bhaduri
# Copyright (c) 2012 Tycho Andersen
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

from multiprocessing import Value

import libqtile.log_utils
import libqtile.manager
import libqtile.utils
import libqtile.hook
import logging
from nose.tools import with_setup, raises

from .utils import Xephyr
from .utils import BareConfig

# TODO: more tests required.
# 1. Check all hooks that can be fired

class TestCall(object):
    def __init__(self, val):
        self.val = val

    def __call__(self, val):
        self.val = val


def setup():
    class Dummy(object):
        pass

    dummy = Dummy()
    libqtile.log_utils.init_log(logging.CRITICAL)
    libqtile.hook.init(dummy)


def teardown():
    libqtile.hook.clear()


@raises(libqtile.utils.QtileError)
def test_cannot_fire_unknown_event():
    libqtile.hook.fire("unknown")


@with_setup(setup, teardown)
def test_hook_calls_subscriber():
    test = TestCall(0)
    libqtile.manager.hook.subscribe.group_window_add(test)
    libqtile.manager.hook.fire("group_window_add", 8)
    assert test.val == 8


@with_setup(setup, teardown)
def test_subscribers_can_be_added_removed():
    test = TestCall(0)
    libqtile.manager.hook.subscribe.group_window_add(test)
    assert libqtile.manager.hook.subscriptions
    libqtile.manager.hook.clear()
    assert not libqtile.manager.hook.subscriptions


@with_setup(setup, teardown)
def test_can_unsubscribe_from_hook():
    test = TestCall(0)

    libqtile.manager.hook.subscribe.group_window_add(test)
    libqtile.manager.hook.fire("group_window_add", 3)
    assert test.val == 3

    libqtile.manager.hook.unsubscribe.group_window_add(test)
    libqtile.manager.hook.fire("group_window_add", 4)
    assert test.val == 3

@Xephyr(True, BareConfig(), False)
def test_can_subscribe_to_startup_hooks(self):

    self.startup_once_calls = Value('i', 0)
    self.startup_calls = Value('i', 0)
    self.startup_complete_calls = Value('i', 0)

    def inc_startup_once_calls():
        self.startup_once_calls.value += 1

    def inc_startup_calls():
        self.startup_calls.value += 1

    def inc_startup_complete_calls():
        self.startup_complete_calls.value += 1

    libqtile.manager.hook.subscribe.startup_once(inc_startup_once_calls)
    libqtile.manager.hook.subscribe.startup(inc_startup_calls)
    libqtile.manager.hook.subscribe.startup_complete(inc_startup_complete_calls)

    self.startQtile(self.config)
    self.start_qtile = True
    assert self.startup_once_calls.value == 1
    assert self.startup_calls.value == 1
    assert self.startup_complete_calls.value == 1
    # TODO Restart and check that startup_once doesn't fire again
