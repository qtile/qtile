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


def assert_focused(self, name):
    """Asserts that window with specified name is currently focused"""
    info = self.c.window.info()
    assert info['name'] == name, 'Got {0!r}, expected {1!r}'.format(
        info['name'], name)


def assert_dimensions(self, x, y, w, h, win=None):
    """Asserts dimensions of window"""
    if win is None:
        win = self.c.window
    info = win.info()
    assert info['x'] == x, info
    assert info['y'] == y, info
    assert info['width'] == w, info  # why?
    assert info['height'] == h, info


def assert_focus_path(self, *names):
    """
    Asserts that subsequent calls to next_window() focus the open windows in
    the given order (and prev_window() in the reverse order)
    """
    for i in names:
        self.c.group.next_window()
        assert_focused(self, i)
    # let's check twice for sure
    for i in names:
        self.c.group.next_window()
        assert_focused(self, i)
    # Ok, let's check backwards now
    for i in reversed(names):
        assert_focused(self, i)
        self.c.group.prev_window()
    # and twice for sure
    for i in reversed(names):
        assert_focused(self, i)
        self.c.group.prev_window()


def assert_focus_path_unordered(self, *names):
    """
    Wrapper of assert_focus_path that allows the actual focus path to be
    different from the given one, as long as:
    1) the focus order is always the same at every forward cycle
    2) the focus order is always the opposite at every reverse cycle
    3) all the windows are selected once and only once at every cycle
    """
    unordered_names = list(names)
    ordered_names = []
    while unordered_names:
        self.c.group.next_window()
        wname = self.c.window.info()['name']
        assert wname in unordered_names
        unordered_names.remove(wname)
        ordered_names.append(wname)
    assert_focus_path(ordered_names)
