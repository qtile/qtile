# Copyright (c) 2022 elParaguayo
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
from libqtile import layout
from libqtile.config import Match
from libqtile.confreader import Config
from test.layouts.layout_utils import assert_dimensions


class ScreenSplitConfig(Config):
    auto_fullscreen = True
    groups = [libqtile.config.Group("a")]
    layouts = [layout.ScreenSplit()]
    floating_layout = libqtile.resources.default_config.floating_layout
    keys = []
    mouse = []
    screens = []
    follow_mouse_focus = False


screensplit_config = pytest.mark.parametrize("manager", [ScreenSplitConfig], indirect=True)


@screensplit_config
def test_screensplit(manager):
    # Max layout is default, occupies top half of screen
    assert manager.c.layout.info()["current_layout"] == "max"
    manager.test_window("one")
    assert_dimensions(manager, 0, 0, 800, 300)
    manager.test_window("two")
    assert_dimensions(manager, 0, 0, 800, 300)
    assert manager.c.layout.info()["current_clients"] == ["one", "two"]

    manager.c.layout.next_split()
    assert manager.c.layout.info()["current_layout"] == "columns"
    assert manager.c.layout.info()["current_clients"] == []

    # Columns layout has no border on single...
    manager.test_window("three")
    assert_dimensions(manager, 0, 300, 800, 300)
    # ... but a border of 2 when multiple windows
    manager.test_window("four")
    assert_dimensions(manager, 400, 300, 396, 296)
    assert manager.c.layout.info()["current_clients"] == ["three", "four"]

    manager.c.layout.next_split()
    assert manager.c.layout.info()["current_layout"] == "max"
    assert manager.c.layout.info()["current_clients"] == ["one", "two"]


@screensplit_config
def test_commands_passthrough(manager):
    assert manager.c.layout.info()["current_layout"] == "max"
    assert "grow_left" not in manager.c.layout.commands()

    manager.c.layout.next_split()
    assert manager.c.layout.info()["current_layout"] == "columns"

    manager.test_window("one")
    assert_dimensions(manager, 0, 300, 800, 300)
    manager.test_window("two")
    assert_dimensions(manager, 400, 300, 396, 296)

    assert "grow_left" in manager.c.layout.commands()
    # Grow window by 40 pixels
    manager.c.layout.grow_left()
    assert_dimensions(manager, 360, 300, 436, 296)


@screensplit_config
def test_move_window_to_split(manager):
    assert manager.c.layout.info()["current_layout"] == "max"
    manager.test_window("one")
    assert_dimensions(manager, 0, 0, 800, 300)

    manager.c.layout.move_window_to_next_split()
    assert manager.c.layout.info()["current_layout"] == "columns"
    assert_dimensions(manager, 0, 300, 800, 300)

    manager.c.layout.move_window_to_previous_split()
    assert manager.c.layout.info()["current_layout"] == "max"
    assert_dimensions(manager, 0, 0, 800, 300)


def test_invalid_splits():
    # Test 1: Missing required keys
    with pytest.raises(ValueError) as e:
        layout.ScreenSplit(splits=[{"rect": (0, 0, 1, 1)}])

    assert str(e.value) == "Splits must define 'name', 'rect' and 'layout'."

    # Test 2: rect is not list/tuple
    with pytest.raises(ValueError) as e:
        layout.ScreenSplit(
            splits=[{"name": "test", "rect": "0, 0, 1, 1", "layout": layout.Max()}]
        )

    assert str(e.value) == "Split rect should be a list/tuple."

    # Test 3: Wrong number of items in rect
    with pytest.raises(ValueError) as e:
        layout.ScreenSplit(splits=[{"name": "test", "rect": (0, 0, 1), "layout": layout.Max()}])

    assert str(e.value) == "Split rect should have 4 float/int members."

    # Test 4: Not all rect items are numbers
    with pytest.raises(ValueError) as e:
        layout.ScreenSplit(
            splits=[{"name": "test", "rect": (0, 0, 1, "1"), "layout": layout.Max()}]
        )

    assert str(e.value) == "Split rect should have 4 float/int members."

    # Test 5: Nested ScreenSplit
    with pytest.raises(ValueError) as e:
        layout.ScreenSplit(
            splits=[{"name": "test", "rect": (0, 0, 1, 1), "layout": layout.ScreenSplit()}]
        )

    assert str(e.value) == "ScreenSplit layouts cannot be nested."

    # Test 6: Matches has invalid object
    with pytest.raises(ValueError) as e:
        layout.ScreenSplit(
            splits=[
                {"name": "test", "rect": (0, 0, 1, 1), "layout": layout.Max(), "matches": [True]}
            ]
        )

    assert str(e.value) == "Invalid object in 'matches'."

    # Test 7: Single match
    with pytest.raises(ValueError) as e:
        layout.ScreenSplit(
            splits=[
                {
                    "name": "test",
                    "rect": (0, 0, 1, 1),
                    "layout": layout.Max(),
                    "matches": Match(wm_class="test"),
                }
            ]
        )

    assert str(e.value) == "'matches' must be a list of 'Match' objects."

    # Test 8: Test valid config - no matches
    s_split = layout.ScreenSplit(
        splits=[{"name": "test", "rect": (0, 0, 1, 1), "layout": layout.Max()}]
    )
    assert s_split

    # Test 9: Test valid config - matches
    s_split = layout.ScreenSplit(
        splits=[
            {
                "name": "test",
                "rect": (0, 0, 1, 1),
                "layout": layout.Max(),
                "matches": [Match(wm_class="test")],
            }
        ]
    )
    assert s_split
