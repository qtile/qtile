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
import libqtile.manager
import libqtile.config
import libqtile.hook
from .layout_utils import assertFocused, assertFocusPathUnordered


class AllLayoutsConfig(object):
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
            Layout = getattr(layout, layout_name)
            try:
                test = issubclass(Layout, layout.base.Layout)
            except TypeError:
                pass
            else:
                # Explicitly exclude the Slice layout, since it depends on
                # other layouts (tested here) and has its own specific tests
                if test and layout_name != 'Slice':
                    yield layout_name, Layout

    @classmethod
    def generate(cls):
        """
        Generate a configuration for each layout currently in the repo.
        Each configuration has only the tested layout (i.e. 1 item) in the
        'layouts' variable.
        """
        return [type(layout_name, (cls, ), {'layouts': [Layout()]})
                for layout_name, Layout in cls.iter_layouts()]


class AllLayouts(AllLayoutsConfig):
    """
    Like AllLayoutsConfig, but all the layouts in the repo are installed
    together in the 'layouts' variable.
    """
    layouts = [Layout() for layout_name, Layout
               in AllLayoutsConfig.iter_layouts()]


each_layout_config = pytest.mark.parametrize("qtile", AllLayoutsConfig.generate(), indirect=True)
all_layouts_config = pytest.mark.parametrize("qtile", [AllLayouts], indirect=True)


@each_layout_config
def test_window_types(qtile):
    qtile.testWindow("one")

    # A dialog should take focus and be floating
    qtile.testDialog("dialog")
    qtile.c.window.info()['floating'] is True
    assertFocused(qtile, "dialog")

    # A notification shouldn't steal focus and should be floating
    qtile.testNotification("notification")
    assert qtile.c.group.info()['focus'] != 'notification'
    qtile.c.group.info_by_name('notification')['floating'] is True


@each_layout_config
def test_focus_cycle(qtile):
    qtile.testWindow("one")
    qtile.testWindow("two")
    qtile.testDialog("float1")
    qtile.testDialog("float2")
    qtile.testWindow("three")

    # Test preconditions (the order of items in 'clients' is managed by each layout)
    assert set(qtile.c.layout.info()['clients']) == {'one', 'two', 'three'}
    assertFocused(qtile, "three")

    # Assert that the layout cycles the focus on all windows
    assertFocusPathUnordered(qtile, 'float1', 'float2', 'one', 'two', 'three')


@each_layout_config
def test_focus_back(qtile):
    # No exception must be raised without windows
    qtile.c.group.focus_back()

    # Nothing must happen with only one window
    one = qtile.testWindow("one")
    qtile.c.group.focus_back()
    assertFocused(qtile, "one")

    # 2 windows
    two = qtile.testWindow("two")
    assertFocused(qtile, "two")
    qtile.c.group.focus_back()
    assertFocused(qtile, "one")
    qtile.c.group.focus_back()
    assertFocused(qtile, "two")

    # Float a window
    three = qtile.testWindow("three")
    qtile.c.group.focus_back()
    assertFocused(qtile, "two")
    qtile.c.window.toggle_floating()
    qtile.c.group.focus_back()
    assertFocused(qtile, "three")

    # If the previous window is killed, the further previous one must be focused
    four = qtile.testWindow("four")
    qtile.kill_window(two)
    qtile.kill_window(three)
    assertFocused(qtile, "four")
    qtile.c.group.focus_back()
    assertFocused(qtile, "one")


@each_layout_config
def test_remove(qtile):
    one = qtile.testWindow("one")
    two = qtile.testWindow("two")
    three = qtile.testWindow("three")
    assertFocused(qtile, "three")
    assert qtile.c.group.info()['focusHistory'] == ["one", "two", "three"]

    # Removing a focused window must focus another (which one depends on the layout)
    qtile.kill_window(three)
    assert qtile.c.window.info()['name'] in qtile.c.layout.info()['clients']

    # To continue testing, explicitly set focus on 'two'
    qtile.c.group.focus_by_name("two")
    four = qtile.testWindow("four")
    assertFocused(qtile, "four")
    assert qtile.c.group.info()['focusHistory'] == ["one", "two", "four"]

    # Removing a non-focused window must not change the current focus
    qtile.kill_window(two)
    assertFocused(qtile, "four")
    assert qtile.c.group.info()['focusHistory'] == ["one", "four"]

    # Add more windows and shuffle the focus order
    five = qtile.testWindow("five")
    six = qtile.testWindow("six")
    qtile.c.group.focus_by_name("one")
    seven = qtile.testWindow("seven")
    qtile.c.group.focus_by_name("six")
    assertFocused(qtile, "six")
    assert qtile.c.group.info()['focusHistory'] == ["four", "five", "one",
                                                    "seven", "six"]

    qtile.kill_window(five)
    qtile.kill_window(one)
    assertFocused(qtile, "six")
    assert qtile.c.group.info()['focusHistory'] == ["four", "seven", "six"]

    qtile.c.group.focus_by_name("seven")
    qtile.kill_window(seven)
    assert qtile.c.window.info()['name'] in qtile.c.layout.info()['clients']


@all_layouts_config
def test_cycle_layouts(qtile):
    qtile.testWindow("one")
    qtile.testWindow("two")
    qtile.testWindow("three")
    qtile.testWindow("four")
    qtile.c.group.focus_by_name("three")
    assertFocused(qtile, "three")

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
