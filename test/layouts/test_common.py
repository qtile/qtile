# Copyright (c) 2017 Dario Giovannetti
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
import libqtile.config
import libqtile.hook
from .layout_utils import assert_focused, assert_focus_path_unordered


class AllLayoutsConfig:
    """
    Ensure that all layouts behave consistently in some common scenarios.
    """
    auto_fullscreen = True
    main = None
    groups = [
        libqtile.config.Group("a"),
        libqtile.config.Group("b"),
        libqtile.config.Group("c"),
        libqtile.config.Group("d"),
    ]
    floating_layout = libqtile.layout.floating.Floating()
    keys = []
    mouse = []
    screens = []

    @staticmethod
    def iter_layouts():
        # Retrieve the layouts dynamically (i.e. do not hard-code a list) to
        # prevent forgetting to add new future layouts
        for layout_name in dir(layout):
            layout_cls = getattr(layout, layout_name)
            try:
                test = issubclass(layout_cls, layout.base.Layout)
            except TypeError:
                pass
            else:
                # Explicitly exclude the Slice layout, since it depends on
                # other layouts (tested here) and has its own specific tests
                if test and layout_name != 'Slice':
                    yield layout_name, layout_cls

    @classmethod
    def generate(cls):
        """
        Generate a configuration for each layout currently in the repo.
        Each configuration has only the tested layout (i.e. 1 item) in the
        'layouts' variable.
        """
        return [type(layout_name, (cls, ), {'layouts': [layout_cls()]})
                for layout_name, layout_cls in cls.iter_layouts()]


class AllLayouts(AllLayoutsConfig):
    """
    Like AllLayoutsConfig, but all the layouts in the repo are installed
    together in the 'layouts' variable.
    """
    layouts = [layout_cls() for layout_name, layout_cls
               in AllLayoutsConfig.iter_layouts()]


class AllLayoutsConfigEvents(AllLayoutsConfig):
    """
    Extends AllLayoutsConfig to test events.
    """
    def main(self, c):
        # TODO: Test more events

        c.test_data = {
            'focus_change': 0,
        }

        def handle_focus_change():
            c.test_data['focus_change'] += 1

        libqtile.hook.subscribe.focus_change(handle_focus_change)


each_layout_config = pytest.mark.parametrize("qtile", AllLayoutsConfig.generate(), indirect=True)
all_layouts_config = pytest.mark.parametrize("qtile", [AllLayouts], indirect=True)
each_layout_config_events = pytest.mark.parametrize("qtile", AllLayoutsConfigEvents.generate(), indirect=True)


@each_layout_config
def test_window_types(qtile):
    pytest.importorskip("tkinter")
    qtile.test_window("one")

    # A dialog should take focus and be floating
    qtile.test_dialog("dialog")
    qtile.c.window.info()['floating'] is True
    assert_focused(qtile, "dialog")

    # A notification shouldn't steal focus and should be floating
    qtile.test_notification("notification")
    assert qtile.c.group.info()['focus'] != 'notification'
    qtile.c.group.info_by_name('notification')['floating'] is True


@each_layout_config
def test_focus_cycle(qtile):
    pytest.importorskip("tkinter")

    qtile.test_window("one")
    qtile.test_window("two")
    qtile.test_dialog("float1")
    qtile.test_dialog("float2")
    qtile.test_window("three")

    # Test preconditions (the order of items in 'clients' is managed by each layout)
    assert set(qtile.c.layout.info()['clients']) == {'one', 'two', 'three'}
    assert_focused(qtile, "three")

    # Assert that the layout cycles the focus on all windows
    assert_focus_path_unordered(qtile, 'float1', 'float2', 'one', 'two', 'three')


@each_layout_config
def test_focus_back(qtile):
    # No exception must be raised without windows
    qtile.c.group.focus_back()

    # Nothing must happen with only one window
    qtile.test_window("one")
    qtile.c.group.focus_back()
    assert_focused(qtile, "one")

    # 2 windows
    two = qtile.test_window("two")
    assert_focused(qtile, "two")
    qtile.c.group.focus_back()
    assert_focused(qtile, "one")
    qtile.c.group.focus_back()
    assert_focused(qtile, "two")

    # Float a window
    three = qtile.test_window("three")
    qtile.c.group.focus_back()
    assert_focused(qtile, "two")
    qtile.c.window.toggle_floating()
    qtile.c.group.focus_back()
    assert_focused(qtile, "three")

    # If the previous window is killed, the further previous one must be focused
    qtile.test_window("four")
    qtile.kill_window(two)
    qtile.kill_window(three)
    assert_focused(qtile, "four")
    qtile.c.group.focus_back()
    assert_focused(qtile, "one")


# TODO: Test more events
@each_layout_config_events
def test_focus_change_event(qtile):
    # Test that the correct number of focus_change events are fired e.g. when
    # opening, closing or switching windows.
    # If for example a layout explicitly fired a focus_change event even though
    # group._Group.focus() or group._Group.remove() already fire one, the other
    # installed layouts would wrongly react to it and cause misbehaviour.
    # In short, this test prevents layouts from influencing each other in
    # unexpected ways.

    # TODO: Why does it start with 2?
    assert qtile.c.get_test_data()['focus_change'] == 2

    # Spawning a window must fire only 1 focus_change event
    one = qtile.test_window("one")
    assert qtile.c.get_test_data()['focus_change'] == 3
    two = qtile.test_window("two")
    assert qtile.c.get_test_data()['focus_change'] == 4
    three = qtile.test_window("three")
    assert qtile.c.get_test_data()['focus_change'] == 5

    # Switching window must fire only 1 focus_change event
    assert_focused(qtile, "three")
    qtile.c.group.focus_by_name("one")
    assert qtile.c.get_test_data()['focus_change'] == 6
    assert_focused(qtile, "one")

    # Focusing the current window must fire another focus_change event
    qtile.c.group.focus_by_name("one")
    assert qtile.c.get_test_data()['focus_change'] == 7

    # Toggling a window floating should not fire focus_change events
    qtile.c.window.toggle_floating()
    assert qtile.c.get_test_data()['focus_change'] == 7
    qtile.c.window.toggle_floating()
    assert qtile.c.get_test_data()['focus_change'] == 7

    # Removing the focused window must fire only 1 focus_change event
    assert_focused(qtile, "one")
    assert qtile.c.group.info()['focus_history'] == ["two", "three", "one"]
    qtile.kill_window(one)
    assert qtile.c.get_test_data()['focus_change'] == 8

    # The position where 'one' was after it was floated and unfloated
    # above depends on the layout, so we can't predict here what window gets
    # selected after killing it; for this reason, focus 'three' explicitly to
    # continue testing
    qtile.c.group.focus_by_name("three")
    assert qtile.c.group.info()['focus_history'] == ["two", "three"]
    assert qtile.c.get_test_data()['focus_change'] == 9

    # Removing a non-focused window must not fire focus_change events
    qtile.kill_window(two)
    assert qtile.c.get_test_data()['focus_change'] == 9
    assert_focused(qtile, "three")

    # Removing the last window must still generate 1 focus_change event
    qtile.kill_window(three)
    assert qtile.c.layout.info()['clients'] == []
    assert qtile.c.get_test_data()['focus_change'] == 10


@each_layout_config
def test_remove(qtile):
    one = qtile.test_window("one")
    two = qtile.test_window("two")
    three = qtile.test_window("three")
    assert_focused(qtile, "three")
    assert qtile.c.group.info()['focus_history'] == ["one", "two", "three"]

    # Removing a focused window must focus another (which one depends on the layout)
    qtile.kill_window(three)
    assert qtile.c.window.info()['name'] in qtile.c.layout.info()['clients']

    # To continue testing, explicitly set focus on 'two'
    qtile.c.group.focus_by_name("two")
    qtile.test_window("four")
    assert_focused(qtile, "four")
    assert qtile.c.group.info()['focus_history'] == ["one", "two", "four"]

    # Removing a non-focused window must not change the current focus
    qtile.kill_window(two)
    assert_focused(qtile, "four")
    assert qtile.c.group.info()['focus_history'] == ["one", "four"]

    # Add more windows and shuffle the focus order
    five = qtile.test_window("five")
    qtile.test_window("six")
    qtile.c.group.focus_by_name("one")
    seven = qtile.test_window("seven")
    qtile.c.group.focus_by_name("six")
    assert_focused(qtile, "six")
    assert qtile.c.group.info()['focus_history'] == ["four", "five", "one",
                                                     "seven", "six"]

    qtile.kill_window(five)
    qtile.kill_window(one)
    assert_focused(qtile, "six")
    assert qtile.c.group.info()['focus_history'] == ["four", "seven", "six"]

    qtile.c.group.focus_by_name("seven")
    qtile.kill_window(seven)
    assert qtile.c.window.info()['name'] in qtile.c.layout.info()['clients']


@each_layout_config
def test_remove_floating(qtile):
    pytest.importorskip("tkinter")

    one = qtile.test_window("one")
    qtile.test_window("two")
    float1 = qtile.test_dialog("float1")
    assert_focused(qtile, "float1")
    assert set(qtile.c.layout.info()['clients']) == {"one", "two"}
    assert qtile.c.group.info()['focus_history'] == ["one", "two", "float1"]

    # Removing a focused floating window must focus the one that was focused before
    qtile.kill_window(float1)
    assert_focused(qtile, "two")
    assert qtile.c.group.info()['focus_history'] == ["one", "two"]

    float2 = qtile.test_dialog("float2")
    assert_focused(qtile, "float2")
    assert qtile.c.group.info()['focus_history'] == ["one", "two", "float2"]

    # Removing a non-focused floating window must not change the current focus
    qtile.c.group.focus_by_name("two")
    qtile.kill_window(float2)
    assert_focused(qtile, "two")
    assert qtile.c.group.info()['focus_history'] == ["one", "two"]

    # Add more windows and shuffle the focus order
    qtile.test_window("three")
    float3 = qtile.test_dialog("float3")
    qtile.c.group.focus_by_name("one")
    float4 = qtile.test_dialog("float4")
    float5 = qtile.test_dialog("float5")
    qtile.c.group.focus_by_name("three")
    qtile.c.group.focus_by_name("float3")
    assert qtile.c.group.info()['focus_history'] == ["two", "one", "float4",
                                                     "float5", "three", "float3"]

    qtile.kill_window(one)
    assert_focused(qtile, "float3")
    assert qtile.c.group.info()['focus_history'] == ["two", "float4",
                                                     "float5", "three", "float3"]

    qtile.kill_window(float5)
    assert_focused(qtile, "float3")
    assert qtile.c.group.info()['focus_history'] == ["two", "float4", "three", "float3"]

    # The focus must be given to the previous window even if it's floating
    qtile.c.group.focus_by_name("float4")
    assert qtile.c.group.info()['focus_history'] == ["two", "three", "float3", "float4"]
    qtile.kill_window(float4)
    assert_focused(qtile, "float3")
    assert qtile.c.group.info()['focus_history'] == ["two", "three", "float3"]

    four = qtile.test_window("four")
    float6 = qtile.test_dialog("float6")
    five = qtile.test_window("five")
    qtile.c.group.focus_by_name("float3")
    assert qtile.c.group.info()['focus_history'] == ["two", "three", "four",
                                                     "float6", "five", "float3"]

    # Killing several unfocused windows before the current one, and then
    # killing the current window, must focus the remaining most recently
    # focused window
    qtile.kill_window(five)
    qtile.kill_window(four)
    qtile.kill_window(float6)
    assert qtile.c.group.info()['focus_history'] == ["two", "three", "float3"]
    qtile.kill_window(float3)
    assert_focused(qtile, "three")
    assert qtile.c.group.info()['focus_history'] == ["two", "three"]


@each_layout_config
def test_desktop_notifications(qtile):
    pytest.importorskip("tkinter")

    # Unlike normal floating windows such as dialogs, notifications don't steal
    # focus when they spawn, so test them separately

    # A notification fired in an empty group must not take focus
    notif1 = qtile.test_notification("notif1")
    assert qtile.c.group.info()['focus'] is None
    qtile.kill_window(notif1)

    # A window is spawned while a notification is displayed
    notif2 = qtile.test_notification("notif2")
    one = qtile.test_window("one")
    assert qtile.c.group.info()['focus_history'] == ["one"]
    qtile.kill_window(notif2)

    # Another notification is fired, but the focus must not change
    notif3 = qtile.test_notification("notif3")
    assert_focused(qtile, 'one')
    qtile.kill_window(notif3)

    # Complicate the scenario with multiple windows and notifications

    dialog1 = qtile.test_dialog("dialog1")
    qtile.test_window("two")
    notif4 = qtile.test_notification("notif4")
    notif5 = qtile.test_notification("notif5")
    assert qtile.c.group.info()['focus_history'] == ["one", "dialog1", "two"]

    dialog2 = qtile.test_dialog("dialog2")
    qtile.kill_window(notif5)
    qtile.test_window("three")
    qtile.kill_window(one)
    qtile.c.group.focus_by_name("two")
    notif6 = qtile.test_notification("notif6")
    notif7 = qtile.test_notification("notif7")
    qtile.kill_window(notif4)
    notif8 = qtile.test_notification("notif8")
    assert qtile.c.group.info()['focus_history'] == ["dialog1", "dialog2",
                                                     "three", "two"]

    qtile.test_dialog("dialog3")
    qtile.kill_window(dialog1)
    qtile.kill_window(dialog2)
    qtile.kill_window(notif6)
    qtile.c.group.focus_by_name("three")
    qtile.kill_window(notif7)
    qtile.kill_window(notif8)
    assert qtile.c.group.info()['focus_history'] == ["two", "dialog3", "three"]


@all_layouts_config
def test_cycle_layouts(qtile):
    qtile.test_window("one")
    qtile.test_window("two")
    qtile.test_window("three")
    qtile.test_window("four")
    qtile.c.group.focus_by_name("three")
    assert_focused(qtile, "three")

    # Cycling all the layouts must keep the current window focused
    initial_layout_name = qtile.c.layout.info()['name']
    while True:
        qtile.c.next_layout()
        if qtile.c.layout.info()['name'] == initial_layout_name:
            break
        # Use qtile.c.layout.info()['name'] in the assertion message, so we
        # know which layout is buggy
        assert qtile.c.window.info()['name'] == "three", qtile.c.layout.info()['name']

    # Now try backwards
    while True:
        qtile.c.prev_layout()
        if qtile.c.layout.info()['name'] == initial_layout_name:
            break
        # Use qtile.c.layout.info()['name'] in the assertion message, so we
        # know which layout is buggy
        assert qtile.c.window.info()['name'] == "three", qtile.c.layout.info()['name']
