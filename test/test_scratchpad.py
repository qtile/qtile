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

import libqtile.layout
import libqtile.bar
import libqtile.widget
import libqtile.manager
import libqtile.config
import libqtile.scratchpad

# import .conftest
from .conftest import retry
from .conftest import no_xinerama
from .layouts.layout_utils import assert_focused, assert_focus_path


class ScratchPadBaseConfic(object):
    auto_fullscreen = True
    main = None
    screens = []
    groups = [
        libqtile.config.ScratchPad('SCRATCHPAD', dropdowns=[
            libqtile.config.DropDown('dd-a', 'xterm -T dd-a', on_focus_lost_hide=False),
            libqtile.config.DropDown('dd-b', 'xterm -T dd-b', on_focus_lost_hide=False),
            libqtile.config.DropDown('dd-c', 'xterm -T dd-c', on_focus_lost_hide=True),
            libqtile.config.DropDown('dd-d', 'xterm -T dd-d', on_focus_lost_hide=True)
        ]),
        libqtile.config.Group("a"),
        libqtile.config.Group("b"),
    ]
    layouts = [libqtile.layout.max.Max()]
    floating_layout = libqtile.layout.floating.Floating()
    keys = []
    mouse = []


# scratchpad_config = lambda x:
def scratchpad_config(x):
    return no_xinerama(pytest.mark.parametrize("qtile", [ScratchPadBaseConfic], indirect=True)(x))


@retry(ignore_exceptions=(KeyError,))
def is_spawned(qtile, name):
    qtile.c.group["SCRATCHPAD"].dropdown_info(name)['window']
    return True


@retry(ignore_exceptions=(ValueError,))
def is_killed(qtile, name):
    if 'window' not in qtile.c.group["SCRATCHPAD"].dropdown_info(name):
        return True
    raise ValueError('not yet killed')


@scratchpad_config
def test_toggling(qtile):
    # adjust command for current display
    qtile.c.group["SCRATCHPAD"].dropdown_reconfigure('dd-a', command='xterm -T dd-a -display %s' % qtile.display)

    qtile.testWindow("one")
    assert qtile.c.group["a"].info()['windows'] == ['one']

    # First toggling: wait for window
    qtile.c.group["SCRATCHPAD"].dropdown_toggle('dd-a')
    is_spawned(qtile, 'dd-a')

    # assert window in current group "a"
    assert sorted(qtile.c.group["a"].info()['windows']) == ['dd-a', 'one']
    assert_focused(qtile, 'dd-a')

    # toggle again --> "hide" xterm in scratchpad group
    qtile.c.group["SCRATCHPAD"].dropdown_toggle('dd-a')
    assert qtile.c.group["a"].info()['windows'] == ['one']
    assert_focused(qtile, 'one')
    assert qtile.c.group["SCRATCHPAD"].info()['windows'] == ['dd-a']

    # toggle again --> show again
    qtile.c.group["SCRATCHPAD"].dropdown_toggle('dd-a')
    assert sorted(qtile.c.group["a"].info()['windows']) == ['dd-a', 'one']
    assert_focused(qtile, 'dd-a')
    assert qtile.c.group["SCRATCHPAD"].info()['windows'] == []


@scratchpad_config
def test_focus_cycle(qtile):
    # adjust command for current display
    qtile.c.group["SCRATCHPAD"].dropdown_reconfigure('dd-a', command='xterm -T dd-a -display %s' % qtile.display)
    qtile.c.group["SCRATCHPAD"].dropdown_reconfigure('dd-b', command='xterm -T dd-b -display %s' % qtile.display)

    qtile.testWindow("one")
    # spawn dd-a by toggling
    assert_focused(qtile, 'one')

    qtile.c.group["SCRATCHPAD"].dropdown_toggle('dd-a')
    is_spawned(qtile, 'dd-a')
    assert_focused(qtile, 'dd-a')

    qtile.testWindow("two")
    assert_focused(qtile, 'two')

    # spawn dd-b by toggling
    qtile.c.group["SCRATCHPAD"].dropdown_toggle('dd-b')
    is_spawned(qtile, 'dd-b')
    assert_focused(qtile, 'dd-b')

    # check all windows
    assert sorted(qtile.c.group["a"].info()['windows']) == ['dd-a', 'dd-b', 'one', 'two']

    assert_focus_path(qtile, 'one', 'two', 'dd-a', 'dd-b')


@scratchpad_config
def test_focus_lost_hide(qtile):
    # adjust command for current display
    qtile.c.group["SCRATCHPAD"].dropdown_reconfigure('dd-c', command='xterm -T dd-c -display %s' % qtile.display)
    qtile.c.group["SCRATCHPAD"].dropdown_reconfigure('dd-d', command='xterm -T dd-d -display %s' % qtile.display)

    qtile.testWindow("one")
    assert_focused(qtile, 'one')

    # spawn dd-c by toggling
    qtile.c.group["SCRATCHPAD"].dropdown_toggle('dd-c')
    is_spawned(qtile, 'dd-c')
    assert_focused(qtile, 'dd-c')
    assert sorted(qtile.c.group["a"].info()['windows']) == ['dd-c', 'one']

    # New Window with Focus --> hide current DropDown
    qtile.testWindow("two")
    assert_focused(qtile, 'two')
    assert sorted(qtile.c.group["a"].info()['windows']) == ['one', 'two']
    assert sorted(qtile.c.group["SCRATCHPAD"].info()['windows']) == ['dd-c']

    # spawn dd-b by toggling
    qtile.c.group["SCRATCHPAD"].dropdown_toggle('dd-d')
    is_spawned(qtile, 'dd-d')
    assert_focused(qtile, 'dd-d')

    assert sorted(qtile.c.group["a"].info()['windows']) == ['dd-d', 'one', 'two']
    assert sorted(qtile.c.group["SCRATCHPAD"].info()['windows']) == ['dd-c']

    # focus next, is the first tiled window --> "hide" dd-d
    qtile.c.group.next_window()
    assert_focused(qtile, 'one')
    assert sorted(qtile.c.group["a"].info()['windows']) == ['one', 'two']
    assert sorted(qtile.c.group["SCRATCHPAD"].info()['windows']) == ['dd-c', 'dd-d']

    # Bring dd-c to front
    qtile.c.group["SCRATCHPAD"].dropdown_toggle('dd-c')
    assert_focused(qtile, 'dd-c')
    assert sorted(qtile.c.group["a"].info()['windows']) == ['dd-c', 'one', 'two']
    assert sorted(qtile.c.group["SCRATCHPAD"].info()['windows']) == ['dd-d']

    # Bring dd-d to front --> "hide dd-c
    qtile.c.group["SCRATCHPAD"].dropdown_toggle('dd-d')
    assert_focused(qtile, 'dd-d')
    assert sorted(qtile.c.group["a"].info()['windows']) == ['dd-d', 'one', 'two']
    assert sorted(qtile.c.group["SCRATCHPAD"].info()['windows']) == ['dd-c']

    # change current group to "b" hids DropDowns
    qtile.c.group['b'].toscreen()
    assert sorted(qtile.c.group["a"].info()['windows']) == ['one', 'two']
    assert sorted(qtile.c.group["SCRATCHPAD"].info()['windows']) == ['dd-c', 'dd-d']


@scratchpad_config
def test_kill(qtile):
    # adjust command for current display
    qtile.c.group["SCRATCHPAD"].dropdown_reconfigure('dd-a', command='xterm -T dd-a -display %s' % qtile.display)

    qtile.testWindow("one")
    assert_focused(qtile, 'one')

    # dd-a has no window associated yet
    assert 'window' not in qtile.c.group["SCRATCHPAD"].dropdown_info('dd-a')

    # First toggling: wait for window
    qtile.c.group["SCRATCHPAD"].dropdown_toggle('dd-a')
    is_spawned(qtile, 'dd-a')
    assert_focused(qtile, 'dd-a')
    assert qtile.c.group["SCRATCHPAD"].dropdown_info('dd-a')['window']['name'] == 'dd-a'

    # kill current window "dd-a"
    qtile.c.window.kill()
    is_killed(qtile, 'dd-a')
    assert_focused(qtile, 'one')
    assert 'window' not in qtile.c.group["SCRATCHPAD"].dropdown_info('dd-a')


@scratchpad_config
def test_floating_toggle(qtile):
    # adjust command for current display
    qtile.c.group["SCRATCHPAD"].dropdown_reconfigure('dd-a', command='xterm -T dd-a -display %s' % qtile.display)

    qtile.testWindow("one")
    assert_focused(qtile, 'one')

    # dd-a has no window associated yet
    assert 'window' not in qtile.c.group["SCRATCHPAD"].dropdown_info('dd-a')
    # First toggling: wait for window
    qtile.c.group["SCRATCHPAD"].dropdown_toggle('dd-a')
    is_spawned(qtile, 'dd-a')
    assert_focused(qtile, 'dd-a')

    assert 'window' in qtile.c.group["SCRATCHPAD"].dropdown_info('dd-a')
    assert sorted(qtile.c.group["a"].info()['windows']) == ['dd-a', 'one']

    qtile.c.window.toggle_floating()
    # dd-a has no window associated any more, but is still in group
    assert 'window' not in qtile.c.group["SCRATCHPAD"].dropdown_info('dd-a')
    assert sorted(qtile.c.group["a"].info()['windows']) == ['dd-a', 'one']

    qtile.c.group["SCRATCHPAD"].dropdown_toggle('dd-a')
    is_spawned(qtile, 'dd-a')
    assert sorted(qtile.c.group["a"].info()['windows']) == ['dd-a', 'dd-a', 'one']
