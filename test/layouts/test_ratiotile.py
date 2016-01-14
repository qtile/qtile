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

from libqtile import layout
import libqtile.manager
import libqtile.config
from time import sleep
from ..utils import Xephyr


class RatioTileConfig:
    auto_fullscreen = True
    main = None
    groups = [
        libqtile.config.Group("a"),
        libqtile.config.Group("b"),
        libqtile.config.Group("c"),
        libqtile.config.Group("d")
    ]
    layouts = [
        layout.RatioTile(ratio=.5),
        layout.RatioTile(),
        ]
    floating_layout = libqtile.layout.floating.Floating()
    keys = []
    mouse = []
    screens = []
    follow_mouse_focus = False


@Xephyr(False, RatioTileConfig())
def test_ratiotile_add_windows(self):
    for i in range(12):
        self.testWindow(str(i))
        if i == 0:
            assert self.c.layout.info()['layout_info'] == [
                (0, 0, 800, 600)]
        elif i == 1:
            assert self.c.layout.info()['layout_info'] == [
                (0, 0, 400, 600), (400, 0, 400, 600)]
        elif i == 2:
            assert self.c.layout.info()['layout_info'] == [
                (0, 0, 266, 600), (266, 0, 266, 600), (532, 0, 268, 600)]
        elif i == 3:
            assert self.c.layout.info()['layout_info'] == [
                (0, 0, 200, 600), (200, 0, 200, 600), (400, 0, 200, 600),
                (600, 0, 200, 600)]
        elif i == 4:
            assert self.c.layout.info()['layout_info'] == [
                (0, 0, 160, 600), (160, 0, 160, 600), (320, 0, 160, 600),
                (480, 0, 160, 600), (640, 0, 160, 600)]
        elif i == 5:
            assert self.c.layout.info()['layout_info'] == [
                (0, 0, 133, 600), (133, 0, 133, 600), (266, 0, 133, 600),
                (399, 0, 133, 600), (532, 0, 133, 600), (665, 0, 135, 600)]
        elif i == 6:
            assert self.c.layout.info()['layout_info'] == [
                (0, 0, 200, 300), (200, 0, 200, 300), (400, 0, 200, 300),
                (600, 0, 200, 300), (0, 300, 266, 300),
                (266, 300, 266, 300), (532, 300, 268, 300)]
        elif i == 7:
            assert self.c.layout.info()['layout_info'] == [
                (0, 0, 200, 300), (200, 0, 200, 300), (400, 0, 200, 300),
                (600, 0, 200, 300), (0, 300, 200, 300),
                (200, 300, 200, 300), (400, 300, 200, 300),
                (600, 300, 200, 300)]
        elif i == 8:
            assert self.c.layout.info()['layout_info'] == [
                (0, 0, 160, 300), (160, 0, 160, 300), (320, 0, 160, 300),
                (480, 0, 160, 300), (640, 0, 160, 300), (0, 300, 200, 300),
                (200, 300, 200, 300), (400, 300, 200, 300),
                (600, 300, 200, 300)]
        elif i == 9:
            assert self.c.layout.info()['layout_info'] == [
                (0, 0, 160, 300), (160, 0, 160, 300), (320, 0, 160, 300),
                (480, 0, 160, 300), (640, 0, 160, 300), (0, 300, 160, 300),
                (160, 300, 160, 300), (320, 300, 160, 300),
                (480, 300, 160, 300), (640, 300, 160, 300)]
        elif i == 10:
            assert self.c.layout.info()['layout_info'] == [
                (0, 0, 133, 300), (133, 0, 133, 300), (266, 0, 133, 300),
                (399, 0, 133, 300), (532, 0, 133, 300), (665, 0, 135, 300),
                (0, 300, 160, 300), (160, 300, 160, 300),
                (320, 300, 160, 300), (480, 300, 160, 300),
                (640, 300, 160, 300)]
        elif i == 11:
            assert self.c.layout.info()['layout_info'] == [
                (0, 0, 133, 300), (133, 0, 133, 300), (266, 0, 133, 300),
                (399, 0, 133, 300), (532, 0, 133, 300), (665, 0, 135, 300),
                (0, 300, 133, 300), (133, 300, 133, 300),
                (266, 300, 133, 300), (399, 300, 133, 300),
                (532, 300, 133, 300), (665, 300, 135, 300)]
        else:
            assert False


@Xephyr(False, RatioTileConfig())
def test_ratiotile_add_windows_golden_ratio(self):
    self.c.next_layout()
    for i in range(12):
        self.testWindow(str(i))
        if i == 0:
            assert self.c.layout.info()['layout_info'] == [
                (0, 0, 800, 600)]
        elif i == 4:
            # the rest test col order
            assert self.c.layout.info()['layout_info'] == [
                (0, 0, 400, 200), (0, 200, 400, 200), (0, 400, 400, 200),
                (400, 0, 400, 300), (400, 300, 400, 300)]
        elif i == 5:
            assert self.c.layout.info()['layout_info'] == [
                (0, 0, 400, 200), (0, 200, 400, 200), (0, 400, 400, 200),
                (400, 0, 400, 200), (400, 200, 400, 200),
                (400, 400, 400, 200)]

        elif i == 9:
            assert self.c.layout.info()['layout_info'] == [
                (0, 0, 266, 150), (0, 150, 266, 150), (0, 300, 266, 150),
                (0, 450, 266, 150), (266, 0, 266, 150),
                (266, 150, 266, 150), (266, 300, 266, 150),
                (266, 450, 266, 150), (532, 0, 266, 300),
                (532, 300, 266, 300)]
        elif i == 10:
            assert self.c.layout.info()['layout_info'] == [
                (0, 0, 266, 150), (0, 150, 266, 150), (0, 300, 266, 150),
                (0, 450, 266, 150), (266, 0, 266, 150),
                (266, 150, 266, 150), (266, 300, 266, 150),
                (266, 450, 266, 150), (532, 0, 266, 200),
                (532, 200, 266, 200), (532, 400, 266, 200)]
        elif i == 11:
            assert self.c.layout.info()['layout_info'] == [
                (0, 0, 266, 150), (0, 150, 266, 150), (0, 300, 266, 150),
                (0, 450, 266, 150), (266, 0, 266, 150),
                (266, 150, 266, 150), (266, 300, 266, 150),
                (266, 450, 266, 150), (532, 0, 266, 150),
                (532, 150, 266, 150), (532, 300, 266, 150),
                (532, 450, 266, 150)]


@Xephyr(False, RatioTileConfig())
def test_ratiotile_basic(self):
    self.testWindow("one")
    self.testWindow("two")
    self.testWindow("three")
    sleep(0.1)
    assert self.c.window.info()['width'] == 264
    assert self.c.window.info()['height'] == 598
    assert self.c.window.info()['x'] == 0
    assert self.c.window.info()['y'] == 0
    assert self.c.window.info()['name'] == 'three'

    self.c.group.next_window()
    assert self.c.window.info()['width'] == 264
    assert self.c.window.info()['height'] == 598
    assert self.c.window.info()['x'] == 266
    assert self.c.window.info()['y'] == 0
    assert self.c.window.info()['name'] == 'two'

    self.c.group.next_window()
    assert self.c.window.info()['width'] == 266
    assert self.c.window.info()['height'] == 598
    assert self.c.window.info()['x'] == 532
    assert self.c.window.info()['y'] == 0
    assert self.c.window.info()['name'] == 'one'
