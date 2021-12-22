# Copyright (c) 2011 Florian Mounier
# Copyright (c) 2012, 2014-2015 Tycho Andersen
# Copyright (c) 2013 Mattias Svala
# Copyright (c) 2013 Craig Barnes
# Copyright (c) 2014 ramnes
# Copyright (c) 2014 Sean Vig
# Copyright (c) 2014 Adi Sieker
# Copyright (c) 2014 Chris Wesseling
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
from test.layouts.layout_utils import assert_dimensions, assert_focus_path, assert_focused


class SliceConfig(Config):
    auto_fullscreen = True
    groups = [
        libqtile.config.Group("a"),
    ]

    layouts = [
        layout.Slice(
            side="left",
            width=200,
            match=Match(title="slice"),
            fallback=layout.Stack(num_stacks=1, border_width=0),
        ),
        layout.Slice(
            side="right",
            width=200,
            match=Match(title="slice"),
            fallback=layout.Stack(num_stacks=1, border_width=0),
        ),
        layout.Slice(
            side="top",
            width=200,
            match=Match(title="slice"),
            fallback=layout.Stack(num_stacks=1, border_width=0),
        ),
        layout.Slice(
            side="bottom",
            width=200,
            match=Match(title="slice"),
            fallback=layout.Stack(num_stacks=1, border_width=0),
        ),
    ]
    floating_layout = libqtile.resources.default_config.floating_layout
    keys = []
    mouse = []
    screens = []
    follow_mouse_focus = False


slice_config = pytest.mark.parametrize("manager", [SliceConfig], indirect=True)


@slice_config
def test_no_slice(manager):
    manager.test_window("one")
    assert_dimensions(manager, 200, 0, 600, 600)
    manager.test_window("two")
    assert_dimensions(manager, 200, 0, 600, 600)


@slice_config
def test_slice_first(manager):
    manager.test_window("slice")
    assert_dimensions(manager, 0, 0, 200, 600)
    manager.test_window("two")
    assert_dimensions(manager, 200, 0, 600, 600)


@slice_config
def test_slice_last(manager):
    manager.test_window("one")
    assert_dimensions(manager, 200, 0, 600, 600)
    manager.test_window("slice")
    assert_dimensions(manager, 0, 0, 200, 600)


@slice_config
def test_slice_focus(manager):
    manager.test_window("one")
    assert_focused(manager, "one")
    two = manager.test_window("two")
    assert_focused(manager, "two")
    slice = manager.test_window("slice")
    assert_focused(manager, "slice")
    assert_focus_path(manager, "slice")
    manager.test_window("three")
    assert_focus_path(manager, "two", "one", "slice", "three")
    manager.kill_window(two)
    assert_focus_path(manager, "one", "slice", "three")
    manager.kill_window(slice)
    assert_focus_path(manager, "one", "three")
    slice = manager.test_window("slice")
    assert_focus_path(manager, "three", "one", "slice")


@slice_config
def test_all_slices(manager):
    manager.test_window("slice")  # left
    assert_dimensions(manager, 0, 0, 200, 600)
    manager.c.next_layout()  # right
    assert_dimensions(manager, 600, 0, 200, 600)
    manager.c.next_layout()  # top
    assert_dimensions(manager, 0, 0, 800, 200)
    manager.c.next_layout()  # bottom
    assert_dimensions(manager, 0, 400, 800, 200)
    manager.c.next_layout()  # left again
    manager.test_window("one")
    assert_dimensions(manager, 200, 0, 600, 600)
    manager.c.next_layout()  # right
    assert_dimensions(manager, 0, 0, 600, 600)
    manager.c.next_layout()  # top
    assert_dimensions(manager, 0, 200, 800, 400)
    manager.c.next_layout()  # bottom
    assert_dimensions(manager, 0, 0, 800, 400)


@slice_config
def test_command_propagation(manager):
    manager.test_window("slice")
    manager.test_window("one")
    manager.test_window("two")
    info = manager.c.layout.info()
    assert info["name"] == "slice"
    org_height = manager.c.window.info()["height"]
    manager.c.layout.toggle_split()
    assert manager.c.window.info()["height"] != org_height
