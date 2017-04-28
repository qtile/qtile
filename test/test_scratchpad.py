# Copyright (c) 2017 Dirk Hartmann
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
import time
import six

import libqtile.layout
import libqtile.bar
import libqtile.widget
import libqtile.manager
import libqtile.config
import libqtile.confreader
from libqtile import command

import libqtile.scratchpad
from libqtile import scratchpad

from libqtile.log_utils import logger

from .layouts.layout_utils import assertFocused

def generate_keys(**kwargs):
    return [libqtile.config.Key( ["control"], '%i'%d,
            scratchpad.DropDown('xterm -display :%i' % d, **kwargs).toggle)
            for d in range(10)]

class ScratchBaseConfic(object):
    screens = []
    groups = [
        libqtile.config.Group("a"),
        libqtile.config.Group("b"),
    ]
    layouts = [libqtile.layout.max.Max()]
    floating_layout = libqtile.layout.floating.Floating()
    mouse = []
    auto_fullscreen = True
    follow_mouse_focus = True
    main = None


class ScratchToggleConfig(ScratchBaseConfic):
    keys = generate_keys(on_focus_lost_hide=False, on_focus_lost_kill=False)

class ScratchHideConfig(ScratchBaseConfic):
    keys = generate_keys(on_focus_lost_hide=True, on_focus_lost_kill=False)

class ScratchKillConfig(ScratchBaseConfic):
    keys = generate_keys(on_focus_lost_hide=False, on_focus_lost_kill=True)


def simulate_keypress_expect_new_window(qtile):
    """
    simulate a keypress and wait for a window to appear.
    There are several DropDown objects created for spawning xterm on different
    displays. 
    """
    # determine current display, and stimulate appropriate keys 
    key = qtile.display[1]
    
    start = len(qtile.c.windows())
    # First keypress --> spawn
    qtile.c.simulate_keypress(["control"], key)
    # wait for window
    for _ in range(100):
        if start < len(qtile.c.windows()):
            break
        time.sleep(0.05)
    else:
        raise AssertionError("Window did not appear...")

def command_expect_kill_window(qtile, cmd):
    """
    execute the given lazy command an d expect a window to be killed.
    This is used for configurations, were the client is killed,
    if it looses focus
    """
    start = len(qtile.c.windows())
    # execute given lazy command
    cmd()
    # wait for window
    for _ in range(100):
        if start >= len(qtile.c.windows()):
            break
        time.sleep(0.05)
    else:
        raise AssertionError("Window could not be killed...")

@pytest.mark.parametrize("qtile", [ScratchToggleConfig], indirect=True)
def test_toggle(qtile):
    qtile.testWindow("one")
    assert qtile.c.group["a"].info()['windows'] == ['one']
    # determine current display, and stimulate appropriate keys 
    key = qtile.display[1]

    # First keypress: wait fro window
    simulate_keypress_expect_new_window(qtile)

    assert sorted(qtile.c.group["a"].info()['windows']) == ['one', 'xterm']
    assertFocused(qtile,'xterm')

    # press again --> hide
    qtile.c.simulate_keypress(["control"], key)
    assert qtile.c.group["a"].info()['windows'] == ['one']
    assertFocused(qtile,'one')
    
    # press again --> show
    qtile.c.simulate_keypress(["control"], key)
    assert sorted(qtile.c.group["a"].info()['windows']) == ['one', 'xterm']
    assertFocused(qtile,'xterm')

    # changing focus twice
    qtile.c.group.next_window()
    assert sorted(qtile.c.group["a"].info()['windows']) == ['one', 'xterm']
    assertFocused(qtile,'one')
    qtile.c.group.next_window()
    assert sorted(qtile.c.group["a"].info()['windows']) == ['one', 'xterm']
    assertFocused(qtile,'xterm')
    
    # press again --> hide
    qtile.c.simulate_keypress(["control"], key)
    assert qtile.c.group["a"].info()['windows'] == ['one']
    assertFocused(qtile,'one')
    
    # changing focus, does not focus the hidden dropdown
    qtile.c.group.next_window()
    assert sorted(qtile.c.group["a"].info()['windows']) == ['one']
    assertFocused(qtile,'one')


@pytest.mark.parametrize("qtile", [ScratchHideConfig], indirect=True)
def test_float_change(qtile):
    qtile.testWindow("one")
    assert qtile.c.group["a"].info()['windows'] == ['one']
    # determine current display, and stimulate appropriate keys 
    key = qtile.display[1]

    # First keypress: wait for window
    simulate_keypress_expect_new_window(qtile)
    assert sorted(qtile.c.group["a"].info()['windows']) == ['one', 'xterm']
    assertFocused(qtile,'xterm')

    # toggle floating, makes the window tiled and focus stays
    qtile.c.window.toggle_floating()
    assert sorted(qtile.c.group["a"].info()['windows']) == ['one', 'xterm']
    assertFocused(qtile,'xterm')
    
    # press again: spawns new process
    simulate_keypress_expect_new_window(qtile)
    assert sorted(qtile.c.group["a"].info()['windows']) == ['one', 'xterm', 'xterm']
    assertFocused(qtile,'xterm')



@pytest.mark.parametrize("qtile", [ScratchHideConfig], indirect=True)
def test_hide(qtile):
    qtile.testWindow("one")
    assert qtile.c.group["a"].info()['windows'] == ['one']
    assert len(qtile.c.windows()) == 1
    # determine current display, and stimulate appropriate keys 
    key = qtile.display[1]

    simulate_keypress_expect_new_window(qtile)

    assert sorted(qtile.c.group["a"].info()['windows']) == ['one', 'xterm']
    assert len(qtile.c.windows()) == 2

    # press again --> hide
    qtile.c.simulate_keypress(["control"], key)
    assert qtile.c.group["a"].info()['windows'] == ['one']
    assert len(qtile.c.windows()) == 2

    # press again --> show
    qtile.c.simulate_keypress(["control"], key)
    assert sorted(qtile.c.group["a"].info()['windows']) == ['one', 'xterm']
    assert len(qtile.c.windows()) == 2
    
    # changing focus twice, will not return focus to dropdown,
    # since first focus changes removes it from group
    qtile.c.group.next_window()
    assert sorted(qtile.c.group["a"].info()['windows']) == ['one']
    assertFocused(qtile,'one')
    qtile.c.group.next_window()
    assert sorted(qtile.c.group["a"].info()['windows']) == ['one']
    assertFocused(qtile,'one')
    assert len(qtile.c.windows()) == 2
    
    # press again --> show
    qtile.c.simulate_keypress(["control"], key)
    assert sorted(qtile.c.group["a"].info()['windows']) == ['one', 'xterm']
    assert len(qtile.c.windows()) == 2
    
    # change group
    qtile.c.group["b"].toscreen()
    assert sorted(qtile.c.group["a"].info()['windows']) == ['one']

    # change group back to a --> dropdown is removed from group
    qtile.c.group["a"].toscreen()
    assert sorted(qtile.c.group["a"].info()['windows']) == ['one']
    assert len(qtile.c.windows()) == 2


@pytest.mark.parametrize("qtile", [ScratchKillConfig], indirect=True)
def test_kill(qtile):
    qtile.testWindow("one")
    assert qtile.c.group["a"].info()['windows'] == ['one']
    assert len(qtile.c.windows()) == 1
    # determine current display, and stimulate appropriate keys 
    key = qtile.display[1]
    
    # press key first time --> spawn and show
    simulate_keypress_expect_new_window(qtile)

    assert sorted(qtile.c.group["a"].info()['windows']) == ['one', 'xterm']
    assert len(qtile.c.windows()) == 2

    # changing focus --> kills
    command_expect_kill_window(qtile, qtile.c.group.next_window)
    assert qtile.c.group["a"].info()['windows'] == ['one']
    assert len(qtile.c.windows()) == 1

    # press again --> spawn again and show
    simulate_keypress_expect_new_window(qtile)
    assert sorted(qtile.c.group["a"].info()['windows']) == ['one', 'xterm']
    assert len(qtile.c.windows()) == 2
    
    # change group to "b" --> kills
    command_expect_kill_window(qtile, qtile.c.group["b"].toscreen)
    assert sorted(qtile.c.group["a"].info()['windows']) == ['one']
    assert len(qtile.c.windows()) == 1
