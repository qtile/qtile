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

import asyncio
import logging

import pytest
from multiprocess import Value

import libqtile.log_utils
import libqtile.utils
from libqtile import hook
from test.conftest import BareConfig

# TODO: more tests required.
# 1. Check all hooks that can be fired


class Call:
    def __init__(self, val):
        self.val = val

    def __call__(self, val):
        self.val = val


@pytest.fixture
def hook_fixture():
    libqtile.log_utils.init_log(logging.CRITICAL, log_path=None, log_color=False)

    yield

    hook.clear()


def test_cannot_fire_unknown_event():
    with pytest.raises(libqtile.utils.QtileError):
        hook.fire("unknown")


@pytest.mark.usefixtures("hook_fixture")
def test_hook_calls_subscriber():
    test = Call(0)
    hook.subscribe.group_window_add(test)
    hook.fire("group_window_add", 8)
    assert test.val == 8


@pytest.mark.usefixtures("hook_fixture")
def test_hook_calls_subscriber_async():
    val = 0

    async def co(new_val):
        nonlocal val
        val = new_val

    hook.subscribe.group_window_add(co)
    hook.fire("group_window_add", 8)

    assert val == 8


@pytest.mark.usefixtures("hook_fixture")
def test_hook_calls_subscriber_async_co():
    val = 0

    async def co(new_val):
        nonlocal val
        val = new_val

    hook.subscribe.group_window_add(co(8))
    hook.fire("group_window_add")

    assert val == 8


@pytest.mark.usefixtures("hook_fixture")
def test_hook_calls_subscriber_async_in_existing_loop():

    async def t():
        val = 0

        async def co(new_val):
            nonlocal val
            val = new_val

        hook.subscribe.group_window_add(co(8))
        hook.fire("group_window_add")
        await asyncio.sleep(0)
        assert val == 8

    asyncio.run(t())


@pytest.mark.usefixtures("hook_fixture")
def test_subscribers_can_be_added_removed():
    test = Call(0)
    hook.subscribe.group_window_add(test)
    assert hook.subscriptions
    hook.clear()
    assert not hook.subscriptions


@pytest.mark.usefixtures("hook_fixture")
def test_can_unsubscribe_from_hook():
    test = Call(0)

    hook.subscribe.group_window_add(test)
    hook.fire("group_window_add", 3)
    assert test.val == 3

    hook.unsubscribe.group_window_add(test)
    hook.fire("group_window_add", 4)
    assert test.val == 3


class SubscribeStartupHooksConfig(BareConfig):
    def __init__(self):
        super().__init__()
        self.startup_once_calls = Value('i', 0)
        self.startup_calls = Value('i', 0)
        self.startup_complete_calls = Value('i', 0)

    def main(self, *args, **kwargs):
        def inc_startup_once_calls():
            self.startup_once_calls.value += 1

        def inc_startup_calls():
            self.startup_calls.value += 1

        def inc_startup_complete_calls():
            self.startup_complete_calls.value += 1

        hook.subscribe.startup_once(inc_startup_once_calls)
        hook.subscribe.startup(inc_startup_calls)
        hook.subscribe.startup_complete(inc_startup_complete_calls)


def test_can_subscribe_to_startup_hooks(manager_nospawn):
    manager = manager_nospawn
    config = SubscribeStartupHooksConfig()
    manager.start(config)
    assert config.startup_once_calls.value == 1
    assert config.startup_calls.value == 1
    assert config.startup_complete_calls.value == 1
    # Restart and check that startup_once doesn't fire again
    manager.terminate()
    manager.start(config, no_spawn=True)
    assert config.startup_once_calls.value == 1
    assert config.startup_calls.value == 2
    assert config.startup_complete_calls.value == 2


@pytest.mark.usefixtures('hook_fixture')
def test_can_update_by_selection_change(manager):
    test = Call(0)
    hook.subscribe.selection_change(test)
    hook.fire('selection_change', 'hello')
    assert test.val == 'hello'


@pytest.mark.usefixtures('hook_fixture')
def test_can_call_by_selection_notify(manager):
    test = Call(0)
    hook.subscribe.selection_notify(test)
    hook.fire('selection_notify', 'hello')
    assert test.val == 'hello'
