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
from multiprocessing import Value

import pytest

import libqtile.log_utils
import libqtile.utils
from libqtile import hook
from libqtile.resources import default_config
from test.conftest import BareConfig
from test.helpers import Retry

# TODO: more tests required.
# 1. Check all hooks that can be fired


class Call:
    def __init__(self, val):
        self.val = val

    def __call__(self, val):
        self.val = val


class NoArgCall(Call):
    def __call__(self):
        self.val += 1


@pytest.fixture
def hook_fixture():
    libqtile.log_utils.init_log()

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


def test_can_subscribe_to_startup_hooks(manager_nospawn):
    config = BareConfig
    for attr in dir(default_config):
        if not hasattr(config, attr):
            setattr(config, attr, getattr(default_config, attr))
    manager = manager_nospawn

    manager.startup_once_calls = Value("i", 0)
    manager.startup_calls = Value("i", 0)
    manager.startup_complete_calls = Value("i", 0)

    def inc_startup_once_calls():
        manager.startup_once_calls.value += 1

    def inc_startup_calls():
        manager.startup_calls.value += 1

    def inc_startup_complete_calls():
        manager.startup_complete_calls.value += 1

    hook.subscribe.startup_once(inc_startup_once_calls)
    hook.subscribe.startup(inc_startup_calls)
    hook.subscribe.startup_complete(inc_startup_complete_calls)

    manager.start(config)
    assert manager.startup_once_calls.value == 1
    assert manager.startup_calls.value == 1
    assert manager.startup_complete_calls.value == 1

    # Restart and check that startup_once doesn't fire again
    manager.terminate()
    manager.start(config, no_spawn=True)
    assert manager.startup_once_calls.value == 1
    assert manager.startup_calls.value == 2
    assert manager.startup_complete_calls.value == 2


@pytest.mark.usefixtures("hook_fixture")
def test_can_update_by_selection_change(manager):
    test = Call(0)
    hook.subscribe.selection_change(test)
    hook.fire("selection_change", "hello")
    assert test.val == "hello"


@pytest.mark.usefixtures("hook_fixture")
def test_can_call_by_selection_notify(manager):
    test = Call(0)
    hook.subscribe.selection_notify(test)
    hook.fire("selection_notify", "hello")
    assert test.val == "hello"


@pytest.mark.usefixtures("hook_fixture")
def test_resume_hook(manager):
    test = NoArgCall(0)
    hook.subscribe.resume(test)
    hook.fire("resume")
    assert test.val == 1


@pytest.mark.usefixtures("hook_fixture")
def test_custom_hook_registry():
    """Tests ability to create custom hook registries"""
    test = NoArgCall(0)

    custom = hook.Registry("test")
    custom.register_hook(hook.Hook("test_hook"))
    custom.subscribe.test_hook(test)

    assert test.val == 0

    # Test ability to fire third party hooks
    custom.fire("test_hook")
    assert test.val == 1

    # Check core hooks are not included in custom registry
    with pytest.raises(libqtile.utils.QtileError):
        custom.fire("client_managed")

    # Check custom hooks are not in core registry
    with pytest.raises(libqtile.utils.QtileError):
        hook.fire("test_hook")


@pytest.mark.usefixtures("hook_fixture")
def test_user_hook(manager_nospawn):
    config = BareConfig
    for attr in dir(default_config):
        if not hasattr(config, attr):
            setattr(config, attr, getattr(default_config, attr))
    manager = manager_nospawn

    manager.custom_no_arg_text = Value("u", "A")
    manager.custom_text = Value("u", "A")

    # Define two functions: first takes no args, second takes a single arg
    def predefined_text():
        with manager.custom_no_arg_text.get_lock():
            manager.custom_no_arg_text.value = "B"

    def defined_text(text):
        with manager.custom_text.get_lock():
            manager.custom_text.value = text

    hook.subscribe.user("set_text")(predefined_text)
    hook.subscribe.user("define_text")(defined_text)

    # Check values are as initialised
    manager.start(config)
    assert manager.custom_no_arg_text.value == "A"
    assert manager.custom_text.value == "A"

    # Check hooked function with no args
    manager.c.fire_user_hook("set_text")
    assert manager.custom_no_arg_text.value == "B"

    # Check hooked function with a single arg
    manager.c.fire_user_hook("define_text", "C")
    assert manager.custom_text.value == "C"


class CallGroupname:
    def __init__(self):
        self.groupname = ""

    def __call__(self, groupname):
        self.groupname = groupname


@Retry(ignore_exceptions=(AssertionError))
def assert_groupname(mgr_nospawn, groupname):
    _, _groupname = mgr_nospawn.c.eval("self.config.test.groupname")
    assert _groupname == groupname


@pytest.mark.usefixtures("hook_fixture")
def test_addgroup(manager_nospawn):
    class AddgroupConfig(BareConfig):
        test = CallGroupname()
        hook.subscribe.addgroup(test)

    manager_nospawn.start(AddgroupConfig)
    assert_groupname(manager_nospawn, "d")


@pytest.mark.usefixtures("hook_fixture")
def test_delgroup(manager_nospawn):
    class DelgroupConfig(BareConfig):
        test = CallGroupname()
        hook.subscribe.delgroup(test)

    manager_nospawn.start(DelgroupConfig)
    manager_nospawn.c.delgroup("d")
    assert_groupname(manager_nospawn, "d")


class CallGroupWindow:
    def __init__(self):
        self.window = ""
        self.group = ""

    def __call__(self, group, win):
        self.group = group.name
        self.window = win.name


@Retry(ignore_exceptions=(AssertionError))
def assert_group_window(mgr_nospawn, group, window):
    _, _group = mgr_nospawn.c.eval("self.config.test.group")
    _, _window = mgr_nospawn.c.eval("self.config.test.window")
    assert _group == group
    assert _window == window


@pytest.mark.usefixtures("hook_fixture")
def test_group_window_add(manager_nospawn):
    class AddGroupWindowConfig(BareConfig):
        test = CallGroupWindow()
        hook.subscribe.group_window_add(test)

    manager_nospawn.start(AddGroupWindowConfig)
    manager_nospawn.test_window("Test Window")
    assert_group_window(manager_nospawn, "a", "Test Window")


@pytest.mark.usefixtures("hook_fixture")
def test_group_window_remove(manager_nospawn):
    class RemoveGroupWindowConfig(BareConfig):
        test = CallGroupWindow()
        hook.subscribe.group_window_remove(test)

    manager_nospawn.start(RemoveGroupWindowConfig)
    manager_nospawn.test_window("Test Window")
    manager_nospawn.c.window.kill()
    assert_group_window(manager_nospawn, "a", "Test Window")


class CallClient:
    def __init__(self):
        self.client = ""

    def __call__(self, client):
        self.client = client.name


@Retry(ignore_exceptions=(AssertionError))
def assert_client(mgr_nospawn, client):
    _, _client = mgr_nospawn.c.eval("self.config.test.client")
    assert _client == client


@pytest.mark.usefixtures("hook_fixture")
def test_client_new(manager_nospawn):
    class ClientNewConfig(BareConfig):
        test = CallClient()
        hook.subscribe.client_new(test)

    manager_nospawn.start(ClientNewConfig)
    manager_nospawn.test_window("Test Client")
    assert_client(manager_nospawn, "Test Client")


@pytest.mark.usefixtures("hook_fixture")
def test_client_managed(manager_nospawn):
    class ClientManagedConfig(BareConfig):
        test = CallClient()
        hook.subscribe.client_managed(test)

    manager_nospawn.start(ClientManagedConfig)
    manager_nospawn.test_window("Test Client")
    assert_client(manager_nospawn, "Test Client")
    manager_nospawn.test_window("Test Static")
    manager_nospawn.c.group.focus_back()
    manager_nospawn.c.window.static()
    assert_client(manager_nospawn, "Test Client")


@pytest.mark.usefixtures("hook_fixture")
def test_client_killed(manager_nospawn):
    class ClientKilledConfig(BareConfig):
        test = CallClient()
        hook.subscribe.client_killed(test)

    manager_nospawn.start(ClientKilledConfig)
    manager_nospawn.test_window("Test Client")
    manager_nospawn.c.window.kill()
    assert_client(manager_nospawn, "Test Client")


@pytest.mark.usefixtures("hook_fixture")
def test_client_focus(manager_nospawn):
    class ClientFocusConfig(BareConfig):
        test = CallClient()
        hook.subscribe.client_focus(test)

    manager_nospawn.start(ClientFocusConfig)
    manager_nospawn.test_window("Test Client")
    assert_client(manager_nospawn, "Test Client")
    manager_nospawn.test_window("Test Focus")
    manager_nospawn.c.group.focus_back()
    assert_client(manager_nospawn, "Test Client")
