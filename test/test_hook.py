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
from libqtile import config, hook, layout
from libqtile.config import Match
from libqtile.resources import default_config
from test.conftest import BareConfig, dualmonitor
from test.helpers import Retry


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
def test_suspend_hook(manager):
    test = NoArgCall(0)
    hook.subscribe.suspend(test)
    hook.fire("suspend")
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


def test_shutdown(manager_nospawn):
    def inc_shutdown_calls():
        manager_nospawn.shutdown_calls.value += 1

    manager_nospawn.shutdown_calls = Value("i", 0)
    hook.subscribe.shutdown(inc_shutdown_calls)

    manager_nospawn.start(BareConfig)
    manager_nospawn.c.shutdown()
    assert manager_nospawn.shutdown_calls.value == 1


@dualmonitor
def test_setgroup(manager_nospawn):
    @Retry(ignore_exceptions=(AssertionError))
    def assert_inc_calls(num: int):
        assert manager_nospawn.setgroup_calls.value == num

    def inc_setgroup_calls():
        manager_nospawn.setgroup_calls.value += 1

    manager_nospawn.setgroup_calls = Value("i", 0)
    hook.subscribe.setgroup(inc_setgroup_calls)

    # Starts with two because of the dual screen
    manager_nospawn.start(BareConfig)
    assert_inc_calls(2)

    manager_nospawn.c.switch_groups("a", "b")
    assert_inc_calls(3)

    manager_nospawn.c.to_screen(1)
    assert_inc_calls(4)
    manager_nospawn.c.to_screen(1)
    assert_inc_calls(4)

    manager_nospawn.c.next_screen()
    assert_inc_calls(5)

    manager_nospawn.c.prev_screen()
    assert_inc_calls(6)

    manager_nospawn.c.group.switch_groups("b")
    assert_inc_calls(7)


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
    manager_nospawn.c.addgroup("e")
    assert_groupname(manager_nospawn, "e")


@pytest.mark.usefixtures("hook_fixture")
def test_delgroup(manager_nospawn):
    class DelgroupConfig(BareConfig):
        test = CallGroupname()
        hook.subscribe.delgroup(test)

    manager_nospawn.start(DelgroupConfig)
    manager_nospawn.c.delgroup("e")
    assert_groupname(manager_nospawn, "")
    manager_nospawn.c.delgroup("d")
    assert_groupname(manager_nospawn, "d")


def test_changegroup(manager_nospawn):
    @Retry(ignore_exceptions=(AssertionError))
    def assert_inc_calls(num: int):
        assert manager_nospawn.changegroup_calls.value == num

    def inc_changegroup_calls():
        manager_nospawn.changegroup_calls.value += 1

    manager_nospawn.changegroup_calls = Value("i", 0)
    hook.subscribe.changegroup(inc_changegroup_calls)

    # Starts with four beacuase of four groups in BareConfig
    manager_nospawn.start(BareConfig)
    assert_inc_calls(4)

    manager_nospawn.c.group.set_label("Test")
    assert_inc_calls(5)

    manager_nospawn.c.addgroup("e")
    assert_inc_calls(6)
    manager_nospawn.c.addgroup("e")
    assert_inc_calls(6)

    manager_nospawn.c.delgroup("e")
    assert_inc_calls(7)
    manager_nospawn.c.delgroup("e")
    assert_inc_calls(7)


def test_focus_change(manager_nospawn):
    @Retry(ignore_exceptions=(AssertionError))
    def assert_inc_calls(num: int):
        assert manager_nospawn.focus_change_calls.value == num

    def inc_focus_change_calls():
        manager_nospawn.focus_change_calls.value += 1

    manager_nospawn.focus_change_calls = Value("i", 0)
    hook.subscribe.focus_change(inc_focus_change_calls)

    manager_nospawn.start(BareConfig)
    assert_inc_calls(1)

    manager_nospawn.test_window("Test Window")
    assert_inc_calls(2)

    manager_nospawn.c.group.focus_by_index(0)
    assert_inc_calls(3)
    manager_nospawn.c.group.focus_by_index(1)
    assert_inc_calls(3)

    manager_nospawn.test_window("Test Focus Change")
    assert_inc_calls(4)

    manager_nospawn.c.group.focus_back()
    assert_inc_calls(5)

    manager_nospawn.c.group.focus_by_name("Test Focus Change")
    assert_inc_calls(6)
    manager_nospawn.c.group.focus_by_name("Test Focus")
    assert_inc_calls(6)

    manager_nospawn.c.group.next_window()
    assert_inc_calls(7)

    manager_nospawn.c.group.prev_window()
    assert_inc_calls(8)

    manager_nospawn.c.window.kill()
    assert_inc_calls(9)


def test_float_change(manager_nospawn):
    @Retry(ignore_exceptions=(AssertionError))
    def assert_inc_calls(num: int):
        assert manager_nospawn.float_change_calls.value == num

    def inc_float_change_calls():
        manager_nospawn.float_change_calls.value += 1

    manager_nospawn.float_change_calls = Value("i", 0)
    hook.subscribe.float_change(inc_float_change_calls)

    manager_nospawn.start(BareConfig)
    manager_nospawn.test_window("Test Window")

    manager_nospawn.c.window.enable_floating()
    assert_inc_calls(1)
    manager_nospawn.c.window.enable_floating()
    assert_inc_calls(1)

    manager_nospawn.c.window.disable_floating()
    assert_inc_calls(2)
    manager_nospawn.c.window.disable_floating()
    assert_inc_calls(2)

    manager_nospawn.c.window.toggle_floating()
    assert_inc_calls(3)

    manager_nospawn.c.window.toggle_floating()
    manager_nospawn.c.window.move_floating(0, 0)
    assert_inc_calls(5)

    manager_nospawn.c.window.toggle_floating()
    manager_nospawn.c.window.resize_floating(10, 10)
    assert_inc_calls(7)

    manager_nospawn.c.window.toggle_floating()
    manager_nospawn.c.window.set_position_floating(0, 0)
    assert_inc_calls(9)

    manager_nospawn.c.window.toggle_floating()
    manager_nospawn.c.window.set_size_floating(100, 100)
    assert_inc_calls(11)


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


class CallWindow:
    def __init__(self):
        self.window = ""

    def __call__(self, window):
        self.window = window.name


@Retry(ignore_exceptions=(AssertionError))
def assert_window(mgr_nospawn, window):
    _, _window = mgr_nospawn.c.eval("self.config.test.window")
    assert _window == window


@pytest.mark.usefixtures("hook_fixture")
def test_client_new(manager_nospawn):
    class ClientNewConfig(BareConfig):
        test = CallWindow()
        hook.subscribe.client_new(test)

    manager_nospawn.start(ClientNewConfig)
    manager_nospawn.test_window("Test Client")
    assert_window(manager_nospawn, "Test Client")


@pytest.mark.usefixtures("hook_fixture")
def test_client_managed(manager_nospawn):
    class ClientManagedConfig(BareConfig):
        test = CallWindow()
        hook.subscribe.client_managed(test)

    manager_nospawn.start(ClientManagedConfig)
    manager_nospawn.test_window("Test Client")
    assert_window(manager_nospawn, "Test Client")

    manager_nospawn.test_window("Test Static")
    manager_nospawn.c.group.focus_back()
    manager_nospawn.c.window.static()
    assert_window(manager_nospawn, "Test Client")


@pytest.mark.usefixtures("hook_fixture")
def test_client_killed(manager_nospawn):
    class ClientKilledConfig(BareConfig):
        test = CallWindow()
        hook.subscribe.client_killed(test)

    manager_nospawn.start(ClientKilledConfig)
    manager_nospawn.test_window("Test Client")
    manager_nospawn.c.window.kill()
    assert_window(manager_nospawn, "Test Client")


@pytest.mark.usefixtures("hook_fixture")
def test_client_focus(manager_nospawn):
    class ClientFocusConfig(BareConfig):
        test = CallWindow()
        hook.subscribe.client_focus(test)

    manager_nospawn.start(ClientFocusConfig)
    manager_nospawn.test_window("Test Client")
    assert_window(manager_nospawn, "Test Client")

    manager_nospawn.test_window("Test Focus")
    manager_nospawn.c.group.focus_back()
    assert_window(manager_nospawn, "Test Client")


@pytest.mark.usefixtures("hook_fixture")
def test_client_mouse_enter(manager_nospawn):
    class ClientMouseEnterConfig(BareConfig):
        test = CallWindow()
        hook.subscribe.client_mouse_enter(test)

    manager_nospawn.start(ClientMouseEnterConfig)
    manager_nospawn.test_window("Test Client")
    manager_nospawn.backend.fake_click(0, 0)
    assert_window(manager_nospawn, "Test Client")


@pytest.mark.usefixtures("hook_fixture")
def test_client_name_updated(manager_nospawn):
    class ClientNameUpdatedConfig(BareConfig):
        test = CallWindow()
        hook.subscribe.client_name_updated(test)

    manager_nospawn.start(ClientNameUpdatedConfig)
    manager_nospawn.test_window("Test Client", new_title="Test NameUpdated")
    assert_window(manager_nospawn, "Test NameUpdated")


@pytest.mark.usefixtures("hook_fixture")
def test_client_urgent_hint_changed(manager_nospawn):
    class ClientUrgentHintChangedConfig(BareConfig):
        groups = [
            config.Group("a"),
            config.Group("b", matches=[Match(title="Test Client")]),
        ]
        test = CallWindow()
        hook.subscribe.client_urgent_hint_changed(test)

    manager_nospawn.start(ClientUrgentHintChangedConfig)
    manager_nospawn.test_window("Test Client", urgent_hint=True)
    assert_window(manager_nospawn, "Test Client")


class CallLayoutGroup:
    def __init__(self):
        self.layout = ""
        self.group = ""

    def __call__(self, layout, group):
        self.layout = layout.name
        self.group = group.name


@Retry(ignore_exceptions=(AssertionError))
def assert_layout_group(mgr_nospawn, layout, group):
    _, _layout = mgr_nospawn.c.eval("self.config.test.layout")
    assert _layout == layout
    _, _group = mgr_nospawn.c.eval("self.config.test.group")
    assert _group == group


@pytest.mark.usefixtures("hook_fixture")
def test_layout_change(manager_nospawn):
    class ClientLayoutChange(BareConfig):
        layouts = [layout.stack.Stack(), layout.columns.Columns()]
        test = CallLayoutGroup()
        hook.subscribe.layout_change(test)

    manager_nospawn.start(ClientLayoutChange)
    assert_layout_group(manager_nospawn, "stack", "a")

    manager_nospawn.c.group.setlayout("columns")
    assert_layout_group(manager_nospawn, "columns", "a")

    manager_nospawn.c.screen.next_group()
    assert_layout_group(manager_nospawn, "stack", "b")

    manager_nospawn.c.screen.prev_group()
    assert_layout_group(manager_nospawn, "columns", "a")

    manager_nospawn.c.screen.toggle_group()
    assert_layout_group(manager_nospawn, "stack", "b")

    manager_nospawn.c.next_layout()
    assert_layout_group(manager_nospawn, "columns", "b")

    manager_nospawn.c.prev_layout()
    assert_layout_group(manager_nospawn, "stack", "b")


@pytest.mark.usefixtures("hook_fixture")
def test_net_wm_icon_change(manager_nospawn, backend_name):
    if backend_name == "wayland":
        pytest.skip("X11 only.")

    class ClientNewConfig(BareConfig):
        test = CallWindow()
        hook.subscribe.net_wm_icon_change(test)

    manager_nospawn.start(ClientNewConfig)
    manager_nospawn.test_window("Test Client")
    assert_window(manager_nospawn, "Test Client")


@pytest.mark.usefixtures("hook_fixture")
def test_screen_change(manager_nospawn):
    @Retry(ignore_exceptions=(AssertionError))
    def assert_inc_calls(num: int):
        assert manager_nospawn.screen_change_calls.value == num

    def inc_screen_change_calls(event):
        manager_nospawn.screen_change_calls.value += 1

    manager_nospawn.screen_change_calls = Value("i", 0)
    hook.subscribe.screen_change(inc_screen_change_calls)

    manager_nospawn.start(BareConfig)
    assert_inc_calls(1)


@pytest.mark.usefixtures("hook_fixture")
def test_screens_reconfigured(manager_nospawn):
    @Retry(ignore_exceptions=(AssertionError))
    def assert_inc_calls(num: int):
        assert manager_nospawn.screens_reconfigured_calls.value == num

    def inc_screens_reconfigured_calls():
        manager_nospawn.screens_reconfigured_calls.value += 1

    manager_nospawn.screens_reconfigured_calls = Value("i", 0)
    hook.subscribe.screens_reconfigured(inc_screens_reconfigured_calls)

    manager_nospawn.start(BareConfig)
    manager_nospawn.c.reconfigure_screens()
    assert_inc_calls(1)


@dualmonitor
@pytest.mark.usefixtures("hook_fixture")
def test_current_screen_change(manager_nospawn):
    @Retry(ignore_exceptions=(AssertionError))
    def assert_inc_calls(num: int):
        assert manager_nospawn.current_screen_change_calls.value == num

    def inc_current_screen_change_calls():
        manager_nospawn.current_screen_change_calls.value += 1

    manager_nospawn.current_screen_change_calls = Value("i", 0)
    hook.subscribe.current_screen_change(inc_current_screen_change_calls)

    manager_nospawn.start(BareConfig)

    manager_nospawn.c.to_screen(1)
    assert_inc_calls(1)
    manager_nospawn.c.to_screen(1)
    assert_inc_calls(1)

    manager_nospawn.c.next_screen()
    assert_inc_calls(2)

    manager_nospawn.c.prev_screen()
    assert_inc_calls(3)
