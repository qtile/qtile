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

import libqtile.config
import libqtile.hook
from libqtile import layout
from libqtile.confreader import Config
from test.layouts.layout_utils import (
    assert_dimensions_fit,
    assert_focus_path_unordered,
    assert_focused,
)


class AllLayoutsConfig(Config):
    """
    Ensure that all layouts behave consistently in some common scenarios.
    """
    groups = [
        libqtile.config.Group("a"),
        libqtile.config.Group("b"),
        libqtile.config.Group("c"),
        libqtile.config.Group("d"),
    ]
    follow_mouse_focus = False
    floating_layout = libqtile.resources.default_config.floating_layout
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


class AllDelegateLayoutsConfig(AllLayoutsConfig):

    @classmethod
    def generate(cls):
        """
        Generate a Slice configuration for each layout currently in the repo.
        Each layout is made a delegate/fallback layout of the Slice layout.
        Each configuration has only the tested layout (i.e. 1 item) in the
        'layouts' variable.
        """
        return [
            type(layout_name, (cls, ), {
                'layouts': [
                    layout.slice.Slice(
                        wname='nevermatch', fallback=layout_cls())]})
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


each_layout_config = pytest.mark.parametrize("self", AllLayoutsConfig.generate(), indirect=True)
all_layouts_config = pytest.mark.parametrize("self", [AllLayouts], indirect=True)
each_layout_config_events = pytest.mark.parametrize("self", AllLayoutsConfigEvents.generate(), indirect=True)
each_delegate_layout_config = pytest.mark.parametrize("self", AllDelegateLayoutsConfig.generate(), indirect=True)


@each_layout_config
def test_window_types(self):
    pytest.importorskip("tkinter")
    self.test_window("one")

    # A dialog should take focus and be floating
    self.test_dialog("dialog")
    self.c.window.info()['floating'] is True
    assert_focused(self, "dialog")

    # A notification shouldn't steal focus and should be floating
    self.test_notification("notification")
    assert self.c.group.info()['focus'] != 'notification'
    self.c.group.info_by_name('notification')['floating'] is True


@each_layout_config
def test_focus_cycle(self):
    pytest.importorskip("tkinter")

    self.test_window("one")
    self.test_window("two")
    self.test_dialog("float1")
    self.test_dialog("float2")
    self.test_window("three")

    # Test preconditions (the order of items in 'clients' is managed by each layout)
    assert set(self.c.layout.info()['clients']) == {'one', 'two', 'three'}
    assert_focused(self, "three")

    # Assert that the layout cycles the focus on all windows
    assert_focus_path_unordered(self, 'float1', 'float2', 'one', 'two', 'three')


@each_layout_config
def test_focus_back(self):
    # No exception must be raised without windows
    self.c.group.focus_back()

    # Nothing must happen with only one window
    self.test_window("one")
    self.c.group.focus_back()
    assert_focused(self, "one")

    # 2 windows
    two = self.test_window("two")
    assert_focused(self, "two")
    self.c.group.focus_back()
    assert_focused(self, "one")
    self.c.group.focus_back()
    assert_focused(self, "two")

    # Float a window
    three = self.test_window("three")
    self.c.group.focus_back()
    assert_focused(self, "two")
    self.c.window.toggle_floating()
    self.c.group.focus_back()
    assert_focused(self, "three")

    # If the previous window is killed, the further previous one must be focused
    self.test_window("four")
    self.kill_window(two)
    self.kill_window(three)
    assert_focused(self, "four")
    self.c.group.focus_back()
    assert_focused(self, "one")


# TODO: Test more events
@each_layout_config_events
def test_focus_change_event(self):
    # Test that the correct number of focus_change events are fired e.g. when
    # opening, closing or switching windows.
    # If for example a layout explicitly fired a focus_change event even though
    # group._Group.focus() or group._Group.remove() already fire one, the other
    # installed layouts would wrongly react to it and cause misbehaviour.
    # In short, this test prevents layouts from influencing each other in
    # unexpected ways.

    # TODO: Why does it start with 2?
    assert self.c.get_test_data()['focus_change'] == 2

    # Spawning a window must fire only 1 focus_change event
    one = self.test_window("one")
    assert self.c.get_test_data()['focus_change'] == 3
    two = self.test_window("two")
    assert self.c.get_test_data()['focus_change'] == 4
    three = self.test_window("three")
    assert self.c.get_test_data()['focus_change'] == 5

    # Switching window must fire only 1 focus_change event
    assert_focused(self, "three")
    self.c.group.focus_by_name("one")
    assert self.c.get_test_data()['focus_change'] == 6
    assert_focused(self, "one")

    # Focusing the current window must fire another focus_change event
    self.c.group.focus_by_name("one")
    assert self.c.get_test_data()['focus_change'] == 7

    # Toggling a window floating should not fire focus_change events
    self.c.window.toggle_floating()
    assert self.c.get_test_data()['focus_change'] == 7
    self.c.window.toggle_floating()
    assert self.c.get_test_data()['focus_change'] == 7

    # Removing the focused window must fire only 1 focus_change event
    assert_focused(self, "one")
    assert self.c.group.info()['focus_history'] == ["two", "three", "one"]
    self.kill_window(one)
    assert self.c.get_test_data()['focus_change'] == 8

    # The position where 'one' was after it was floated and unfloated
    # above depends on the layout, so we can't predict here what window gets
    # selected after killing it; for this reason, focus 'three' explicitly to
    # continue testing
    self.c.group.focus_by_name("three")
    assert self.c.group.info()['focus_history'] == ["two", "three"]
    assert self.c.get_test_data()['focus_change'] == 9

    # Removing a non-focused window must not fire focus_change events
    self.kill_window(two)
    assert self.c.get_test_data()['focus_change'] == 9
    assert_focused(self, "three")

    # Removing the last window must still generate 1 focus_change event
    self.kill_window(three)
    assert self.c.layout.info()['clients'] == []
    assert self.c.get_test_data()['focus_change'] == 10


@each_layout_config
def test_remove(self):
    one = self.test_window("one")
    two = self.test_window("two")
    three = self.test_window("three")
    assert_focused(self, "three")
    assert self.c.group.info()['focus_history'] == ["one", "two", "three"]

    # Removing a focused window must focus another (which one depends on the layout)
    self.kill_window(three)
    assert self.c.window.info()['name'] in self.c.layout.info()['clients']

    # To continue testing, explicitly set focus on 'two'
    self.c.group.focus_by_name("two")
    self.test_window("four")
    assert_focused(self, "four")
    assert self.c.group.info()['focus_history'] == ["one", "two", "four"]

    # Removing a non-focused window must not change the current focus
    self.kill_window(two)
    assert_focused(self, "four")
    assert self.c.group.info()['focus_history'] == ["one", "four"]

    # Add more windows and shuffle the focus order
    five = self.test_window("five")
    self.test_window("six")
    self.c.group.focus_by_name("one")
    seven = self.test_window("seven")
    self.c.group.focus_by_name("six")
    assert_focused(self, "six")
    assert self.c.group.info()['focus_history'] == ["four", "five", "one",
                                                    "seven", "six"]

    self.kill_window(five)
    self.kill_window(one)
    assert_focused(self, "six")
    assert self.c.group.info()['focus_history'] == ["four", "seven", "six"]

    self.c.group.focus_by_name("seven")
    self.kill_window(seven)
    assert self.c.window.info()['name'] in self.c.layout.info()['clients']


@each_layout_config
def test_remove_floating(self):
    pytest.importorskip("tkinter")

    one = self.test_window("one")
    self.test_window("two")
    float1 = self.test_dialog("float1")
    assert_focused(self, "float1")
    assert set(self.c.layout.info()['clients']) == {"one", "two"}
    assert self.c.group.info()['focus_history'] == ["one", "two", "float1"]

    # Removing a focused floating window must focus the one that was focused before
    self.kill_window(float1)
    assert_focused(self, "two")
    assert self.c.group.info()['focus_history'] == ["one", "two"]

    float2 = self.test_dialog("float2")
    assert_focused(self, "float2")
    assert self.c.group.info()['focus_history'] == ["one", "two", "float2"]

    # Removing a non-focused floating window must not change the current focus
    self.c.group.focus_by_name("two")
    self.kill_window(float2)
    assert_focused(self, "two")
    assert self.c.group.info()['focus_history'] == ["one", "two"]

    # Add more windows and shuffle the focus order
    self.test_window("three")
    float3 = self.test_dialog("float3")
    self.c.group.focus_by_name("one")
    float4 = self.test_dialog("float4")
    float5 = self.test_dialog("float5")
    self.c.group.focus_by_name("three")
    self.c.group.focus_by_name("float3")
    assert self.c.group.info()['focus_history'] == ["two", "one", "float4",
                                                    "float5", "three", "float3"]

    self.kill_window(one)
    assert_focused(self, "float3")
    assert self.c.group.info()['focus_history'] == ["two", "float4",
                                                    "float5", "three", "float3"]

    self.kill_window(float5)
    assert_focused(self, "float3")
    assert self.c.group.info()['focus_history'] == ["two", "float4", "three", "float3"]

    # The focus must be given to the previous window even if it's floating
    self.c.group.focus_by_name("float4")
    assert self.c.group.info()['focus_history'] == ["two", "three", "float3", "float4"]
    self.kill_window(float4)
    assert_focused(self, "float3")
    assert self.c.group.info()['focus_history'] == ["two", "three", "float3"]

    four = self.test_window("four")
    float6 = self.test_dialog("float6")
    five = self.test_window("five")
    self.c.group.focus_by_name("float3")
    assert self.c.group.info()['focus_history'] == ["two", "three", "four",
                                                    "float6", "five", "float3"]

    # Killing several unfocused windows before the current one, and then
    # killing the current window, must focus the remaining most recently
    # focused window
    self.kill_window(five)
    self.kill_window(four)
    self.kill_window(float6)
    assert self.c.group.info()['focus_history'] == ["two", "three", "float3"]
    self.kill_window(float3)
    assert_focused(self, "three")
    assert self.c.group.info()['focus_history'] == ["two", "three"]


@each_layout_config
def test_desktop_notifications(self):
    pytest.importorskip("tkinter")

    # Unlike normal floating windows such as dialogs, notifications don't steal
    # focus when they spawn, so test them separately

    # A notification fired in an empty group must not take focus
    notif1 = self.test_notification("notif1")
    assert self.c.group.info()['focus'] is None
    self.kill_window(notif1)

    # A window is spawned while a notification is displayed
    notif2 = self.test_notification("notif2")
    one = self.test_window("one")
    assert self.c.group.info()['focus_history'] == ["one"]
    self.kill_window(notif2)

    # Another notification is fired, but the focus must not change
    notif3 = self.test_notification("notif3")
    assert_focused(self, 'one')
    self.kill_window(notif3)

    # Complicate the scenario with multiple windows and notifications

    dialog1 = self.test_dialog("dialog1")
    self.test_window("two")
    notif4 = self.test_notification("notif4")
    notif5 = self.test_notification("notif5")
    assert self.c.group.info()['focus_history'] == ["one", "dialog1", "two"]

    dialog2 = self.test_dialog("dialog2")
    self.kill_window(notif5)
    self.test_window("three")
    self.kill_window(one)
    self.c.group.focus_by_name("two")
    notif6 = self.test_notification("notif6")
    notif7 = self.test_notification("notif7")
    self.kill_window(notif4)
    notif8 = self.test_notification("notif8")
    assert self.c.group.info()['focus_history'] == ["dialog1", "dialog2",
                                                    "three", "two"]

    self.test_dialog("dialog3")
    self.kill_window(dialog1)
    self.kill_window(dialog2)
    self.kill_window(notif6)
    self.c.group.focus_by_name("three")
    self.kill_window(notif7)
    self.kill_window(notif8)
    assert self.c.group.info()['focus_history'] == ["two", "dialog3", "three"]


@each_delegate_layout_config
def test_only_uses_delegated_screen_rect(self):
    self.test_window("one")
    self.c.group.focus_by_name("one")
    assert_focused(self, "one")
    assert_dimensions_fit(self, 256, 0, 800-256, 600)


@all_layouts_config
def test_cycle_layouts(self):
    self.test_window("one")
    self.test_window("two")
    self.test_window("three")
    self.test_window("four")
    self.c.group.focus_by_name("three")
    assert_focused(self, "three")

    # Cycling all the layouts must keep the current window focused
    initial_layout_name = self.c.layout.info()['name']
    while True:
        self.c.next_layout()
        if self.c.layout.info()['name'] == initial_layout_name:
            break
        # Use self.c.layout.info()['name'] in the assertion message, so we
        # know which layout is buggy
        assert self.c.window.info()['name'] == "three", self.c.layout.info()['name']

    # Now try backwards
    while True:
        self.c.prev_layout()
        if self.c.layout.info()['name'] == initial_layout_name:
            break
        # Use self.c.layout.info()['name'] in the assertion message, so we
        # know which layout is buggy
        assert self.c.window.info()['name'] == "three", self.c.layout.info()['name']
