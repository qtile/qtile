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

import logging
from multiprocessing import Value

import pytest

import libqtile.core
import libqtile.hook
import libqtile.log_utils
import libqtile.utils
from libqtile.resources import default_config
from test.conftest import BareConfig

# TODO: more tests required.
# 1. Check all hooks that can be fired


class Call:
    def __init__(self, val):
        self.val = val

    def __call__(self, val):
        self.val = val


@pytest.yield_fixture
def hook_fixture():
    class Dummy:
        pass

    dummy = Dummy()
    libqtile.log_utils.init_log(logging.CRITICAL, log_path=None, log_color=False)
    libqtile.hook.init(dummy)

    yield

    libqtile.hook.clear()


def test_cannot_fire_unknown_event():
    with pytest.raises(libqtile.utils.QtileError):
        libqtile.hook.fire("unknown")


@pytest.mark.usefixtures("hook_fixture")
def test_hook_calls_subscriber():
    test = Call(0)
    libqtile.core.manager.hook.subscribe.group_window_add(test)
    libqtile.core.manager.hook.fire("group_window_add", 8)
    assert test.val == 8


@pytest.mark.usefixtures("hook_fixture")
def test_subscribers_can_be_added_removed():
    test = Call(0)
    libqtile.core.manager.hook.subscribe.group_window_add(test)
    assert libqtile.core.manager.hook.subscriptions
    libqtile.core.manager.hook.clear()
    assert not libqtile.core.manager.hook.subscriptions


@pytest.mark.usefixtures("hook_fixture")
def test_can_unsubscribe_from_hook():
    test = Call(0)

    libqtile.core.manager.hook.subscribe.group_window_add(test)
    libqtile.core.manager.hook.fire("group_window_add", 3)
    assert test.val == 3

    libqtile.core.manager.hook.unsubscribe.group_window_add(test)
    libqtile.core.manager.hook.fire("group_window_add", 4)
    assert test.val == 3


def test_can_subscribe_to_startup_hooks(qtile_nospawn):
    config = BareConfig
    for attr in dir(default_config):
        if not hasattr(config, attr):
            setattr(config, attr, getattr(default_config, attr))
    self = qtile_nospawn

    self.startup_once_calls = Value('i', 0)
    self.startup_calls = Value('i', 0)
    self.startup_complete_calls = Value('i', 0)

    def inc_startup_once_calls():
        self.startup_once_calls.value += 1

    def inc_startup_calls():
        self.startup_calls.value += 1

    def inc_startup_complete_calls():
        self.startup_complete_calls.value += 1

    libqtile.core.manager.hook.subscribe.startup_once(inc_startup_once_calls)
    libqtile.core.manager.hook.subscribe.startup(inc_startup_calls)
    libqtile.core.manager.hook.subscribe.startup_complete(inc_startup_complete_calls)

    self.start(config)
    self.start_qtile = True
    assert self.startup_once_calls.value == 1
    assert self.startup_calls.value == 1
    assert self.startup_complete_calls.value == 1
    # TODO Restart and check that startup_once doesn't fire again


@pytest.mark.usefixtures('hook_fixture')
def test_can_update_by_selection_change(qtile):
    test = Call(0)
    libqtile.core.manager.hook.subscribe.selection_change(test)
    libqtile.core.manager.hook.fire('selection_change', 'hello')
    assert test.val == 'hello'


@pytest.mark.usefixtures('hook_fixture')
def test_can_call_by_selection_notify(qtile):
    test = Call(0)
    libqtile.core.manager.hook.subscribe.selection_notify(test)
    libqtile.core.manager.hook.fire('selection_notify', 'hello')
    assert test.val == 'hello'
