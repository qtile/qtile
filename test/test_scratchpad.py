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

import libqtile.config
import libqtile.layout
import libqtile.widget
from libqtile.confreader import Config
from test.conftest import Retry, no_xinerama
from test.layouts.layout_utils import assert_focus_path, assert_focused


class ScratchPadBaseConfic(Config):
    auto_fullscreen = True
    screens = []
    groups = [
        libqtile.config.ScratchPad('SCRATCHPAD', dropdowns=[
            libqtile.config.DropDown('dd-a', 'xterm -T dd-a sh', on_focus_lost_hide=False),
            libqtile.config.DropDown('dd-b', 'xterm -T dd-b sh', on_focus_lost_hide=False),
            libqtile.config.DropDown('dd-c', 'xterm -T dd-c sh', on_focus_lost_hide=True),
            libqtile.config.DropDown('dd-d', 'xterm -T dd-d sh', on_focus_lost_hide=True)
        ]),
        libqtile.config.Group("a"),
        libqtile.config.Group("b"),
    ]
    layouts = [libqtile.layout.max.Max()]
    floating_layout = libqtile.resources.default_config.floating_layout
    keys = []
    mouse = []


# scratchpad_config = lambda x:
def scratchpad_config(x):
    return no_xinerama(pytest.mark.parametrize("self", [ScratchPadBaseConfic], indirect=True)(x))


@Retry(ignore_exceptions=(KeyError,))
def is_spawned(self, name):
    self.c.group["SCRATCHPAD"].dropdown_info(name)['window']
    return True


@Retry(ignore_exceptions=(ValueError,))
def is_killed(self, name):
    if 'window' not in self.c.group["SCRATCHPAD"].dropdown_info(name):
        return True
    raise ValueError('not yet killed')


@scratchpad_config
def test_toggling(self):
    # adjust command for current display
    self.c.group["SCRATCHPAD"].dropdown_reconfigure('dd-a', command='xterm -T dd-a -display %s sh' % self.display)

    self.test_window("one")
    assert self.c.group["a"].info()['windows'] == ['one']

    # First toggling: wait for window
    self.c.group["SCRATCHPAD"].dropdown_toggle('dd-a')
    is_spawned(self, 'dd-a')

    # assert window in current group "a"
    assert sorted(self.c.group["a"].info()['windows']) == ['dd-a', 'one']
    assert_focused(self, 'dd-a')

    # toggle again --> "hide" xterm in scratchpad group
    self.c.group["SCRATCHPAD"].dropdown_toggle('dd-a')
    assert self.c.group["a"].info()['windows'] == ['one']
    assert_focused(self, 'one')
    assert self.c.group["SCRATCHPAD"].info()['windows'] == ['dd-a']

    # toggle again --> show again
    self.c.group["SCRATCHPAD"].dropdown_toggle('dd-a')
    assert sorted(self.c.group["a"].info()['windows']) == ['dd-a', 'one']
    assert_focused(self, 'dd-a')
    assert self.c.group["SCRATCHPAD"].info()['windows'] == []


@scratchpad_config
def test_focus_cycle(self):
    # adjust command for current display
    self.c.group["SCRATCHPAD"].dropdown_reconfigure('dd-a', command='xterm -T dd-a -display %s sh' % self.display)
    self.c.group["SCRATCHPAD"].dropdown_reconfigure('dd-b', command='xterm -T dd-b -display %s sh' % self.display)

    self.test_window("one")
    # spawn dd-a by toggling
    assert_focused(self, 'one')

    self.c.group["SCRATCHPAD"].dropdown_toggle('dd-a')
    is_spawned(self, 'dd-a')
    assert_focused(self, 'dd-a')

    self.test_window("two")
    assert_focused(self, 'two')

    # spawn dd-b by toggling
    self.c.group["SCRATCHPAD"].dropdown_toggle('dd-b')
    is_spawned(self, 'dd-b')
    assert_focused(self, 'dd-b')

    # check all windows
    assert sorted(self.c.group["a"].info()['windows']) == ['dd-a', 'dd-b', 'one', 'two']

    assert_focus_path(self, 'one', 'two', 'dd-a', 'dd-b')


@scratchpad_config
def test_focus_lost_hide(self):
    # adjust command for current display
    self.c.group["SCRATCHPAD"].dropdown_reconfigure('dd-c', command='xterm -T dd-c -display %s sh' % self.display)
    self.c.group["SCRATCHPAD"].dropdown_reconfigure('dd-d', command='xterm -T dd-d -display %s sh' % self.display)

    self.test_window("one")
    assert_focused(self, 'one')

    # spawn dd-c by toggling
    self.c.group["SCRATCHPAD"].dropdown_toggle('dd-c')
    is_spawned(self, 'dd-c')
    assert_focused(self, 'dd-c')
    assert sorted(self.c.group["a"].info()['windows']) == ['dd-c', 'one']

    # New Window with Focus --> hide current DropDown
    self.test_window("two")
    assert_focused(self, 'two')
    assert sorted(self.c.group["a"].info()['windows']) == ['one', 'two']
    assert sorted(self.c.group["SCRATCHPAD"].info()['windows']) == ['dd-c']

    # spawn dd-b by toggling
    self.c.group["SCRATCHPAD"].dropdown_toggle('dd-d')
    is_spawned(self, 'dd-d')
    assert_focused(self, 'dd-d')

    assert sorted(self.c.group["a"].info()['windows']) == ['dd-d', 'one', 'two']
    assert sorted(self.c.group["SCRATCHPAD"].info()['windows']) == ['dd-c']

    # focus next, is the first tiled window --> "hide" dd-d
    self.c.group.next_window()
    assert_focused(self, 'one')
    assert sorted(self.c.group["a"].info()['windows']) == ['one', 'two']
    assert sorted(self.c.group["SCRATCHPAD"].info()['windows']) == ['dd-c', 'dd-d']

    # Bring dd-c to front
    self.c.group["SCRATCHPAD"].dropdown_toggle('dd-c')
    assert_focused(self, 'dd-c')
    assert sorted(self.c.group["a"].info()['windows']) == ['dd-c', 'one', 'two']
    assert sorted(self.c.group["SCRATCHPAD"].info()['windows']) == ['dd-d']

    # Bring dd-d to front --> "hide dd-c
    self.c.group["SCRATCHPAD"].dropdown_toggle('dd-d')
    assert_focused(self, 'dd-d')
    assert sorted(self.c.group["a"].info()['windows']) == ['dd-d', 'one', 'two']
    assert sorted(self.c.group["SCRATCHPAD"].info()['windows']) == ['dd-c']

    # change current group to "b" hids DropDowns
    self.c.group['b'].toscreen()
    assert sorted(self.c.group["a"].info()['windows']) == ['one', 'two']
    assert sorted(self.c.group["SCRATCHPAD"].info()['windows']) == ['dd-c', 'dd-d']


@scratchpad_config
def test_kill(self):
    # adjust command for current display
    self.c.group["SCRATCHPAD"].dropdown_reconfigure('dd-a', command='xterm -T dd-a -display %s sh' % self.display)

    self.test_window("one")
    assert_focused(self, 'one')

    # dd-a has no window associated yet
    assert 'window' not in self.c.group["SCRATCHPAD"].dropdown_info('dd-a')

    # First toggling: wait for window
    self.c.group["SCRATCHPAD"].dropdown_toggle('dd-a')
    is_spawned(self, 'dd-a')
    assert_focused(self, 'dd-a')
    assert self.c.group["SCRATCHPAD"].dropdown_info('dd-a')['window']['name'] == 'dd-a'

    # kill current window "dd-a"
    self.c.window.kill()
    is_killed(self, 'dd-a')
    assert_focused(self, 'one')
    assert 'window' not in self.c.group["SCRATCHPAD"].dropdown_info('dd-a')


@scratchpad_config
def test_floating_toggle(self):
    # adjust command for current display
    self.c.group["SCRATCHPAD"].dropdown_reconfigure('dd-a', command='xterm -T dd-a -display %s sh' % self.display)

    self.test_window("one")
    assert_focused(self, 'one')

    # dd-a has no window associated yet
    assert 'window' not in self.c.group["SCRATCHPAD"].dropdown_info('dd-a')
    # First toggling: wait for window
    self.c.group["SCRATCHPAD"].dropdown_toggle('dd-a')
    is_spawned(self, 'dd-a')
    assert_focused(self, 'dd-a')

    assert 'window' in self.c.group["SCRATCHPAD"].dropdown_info('dd-a')
    assert sorted(self.c.group["a"].info()['windows']) == ['dd-a', 'one']

    self.c.window.toggle_floating()
    # dd-a has no window associated any more, but is still in group
    assert 'window' not in self.c.group["SCRATCHPAD"].dropdown_info('dd-a')
    assert sorted(self.c.group["a"].info()['windows']) == ['dd-a', 'one']

    self.c.group["SCRATCHPAD"].dropdown_toggle('dd-a')
    is_spawned(self, 'dd-a')
    assert sorted(self.c.group["a"].info()['windows']) == ['dd-a', 'dd-a', 'one']


@scratchpad_config
def test_stepping_between_groups_should_skip_scratchpads(self):
    # we are on a group
    self.c.screen.next_group()
    # we are on b group
    self.c.screen.next_group()
    # we should be on a group
    assert self.c.group.info()["name"] == "a"

    self.c.screen.prev_group()
    # we should be on b group
    assert self.c.group.info()["name"] == "b"
