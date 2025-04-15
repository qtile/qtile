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


@pytest.fixture(scope="function")
def ss_manager(manager_nospawn, request):
    class ScreenSplitConfig(Config):
        auto_fullscreen = True
        groups = [libqtile.config.Group("a")]
        layouts = [layout.ScreenSplit(**getattr(request, "param", dict()))]
        floating_layout = libqtile.resources.default_config.floating_layout
        keys = []
        mouse = []
        screens = []
        follow_mouse_focus = False

    manager_nospawn.start(ScreenSplitConfig)

    yield manager_nospawn


def ss_config(**kwargs):
    return pytest.mark.parametrize("ss_manager", [kwargs], indirect=True)


@ss_config()
def test_screensplit(ss_manager):
    # Max layout is default, occupies top half of screen
    assert ss_manager.c.layout.info()["current_layout"] == "max"
    ss_manager.test_window("one")
    assert_dimensions(ss_manager, 0, 0, 800, 300)
    ss_manager.test_window("two")
    assert_dimensions(ss_manager, 0, 0, 800, 300)
    assert ss_manager.c.layout.info()["current_clients"] == ["one", "two"]

    ss_manager.c.layout.next_split()
    assert ss_manager.c.layout.info()["current_layout"] == "columns"
    assert ss_manager.c.layout.info()["current_clients"] == []

    # Columns layout has no border on single...
    ss_manager.test_window("three")
    assert_dimensions(ss_manager, 0, 300, 800, 300)
    # ... but a border of 2 when multiple windows
    ss_manager.test_window("four")
    assert_dimensions(ss_manager, 400, 300, 396, 296)
    assert ss_manager.c.layout.info()["current_clients"] == ["three", "four"]

    ss_manager.c.layout.next_split()
    assert ss_manager.c.layout.info()["current_layout"] == "max"
    assert ss_manager.c.layout.info()["current_clients"] == ["one", "two"]


@ss_config()
def test_commands_passthrough(ss_manager):
    assert ss_manager.c.layout.info()["current_layout"] == "max"
    assert "grow_left" not in ss_manager.c.layout.commands()

    ss_manager.c.layout.next_split()
    assert ss_manager.c.layout.info()["current_layout"] == "columns"

    ss_manager.test_window("one")
    assert_dimensions(ss_manager, 0, 300, 800, 300)
    ss_manager.test_window("two")
    assert_dimensions(ss_manager, 400, 300, 396, 296)

    assert "grow_left" in ss_manager.c.layout.commands()
    # Grow window by 40 pixels
    ss_manager.c.layout.grow_left()
    assert_dimensions(ss_manager, 360, 300, 436, 296)


@ss_config()
def test_move_window_to_split(ss_manager):
    assert ss_manager.c.layout.info()["current_layout"] == "max"
    ss_manager.test_window("one")
    assert_dimensions(ss_manager, 0, 0, 800, 300)

    ss_manager.c.layout.move_window_to_next_split()
    assert ss_manager.c.layout.info()["current_layout"] == "columns"
    assert_dimensions(ss_manager, 0, 300, 800, 300)

    ss_manager.c.layout.move_window_to_previous_split()
    assert ss_manager.c.layout.info()["current_layout"] == "max"
    assert_dimensions(ss_manager, 0, 0, 800, 300)


@ss_config(
    splits=[
        {
            "name": "no_match",
            "rect": (0, 0, 1, 0.5),
            "layout": layout.Max(),
        },
        {
            "name": "match",
            "rect": (0, 0.5, 1, 0.5),
            "layout": layout.Spiral(),
            "matches": [Match(title="test")],
        },
    ]
)
def test_match_window(ss_manager):
    assert ss_manager.c.layout.info()["current_layout"] == "max"
    ss_manager.test_window("one")
    assert ss_manager.c.layout.info()["current_layout"] == "max"

    ss_manager.test_window("test")
    assert ss_manager.c.layout.info()["current_layout"] == "spiral"


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
