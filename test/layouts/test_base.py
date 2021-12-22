# Copyright (c) 2021 Jeroen Wijenbergh
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

import libqtile
from libqtile.confreader import Config
from libqtile.layout.base import _SimpleLayoutBase


class DummyLayout(_SimpleLayoutBase):
    defaults = [
        ("current_offset", 0, ""),
        ("current_position", None, ""),
    ]

    def __init__(self, **config):
        _SimpleLayoutBase.__init__(self, **config)
        self.add_defaults(DummyLayout.defaults)

    def add(self, client):
        return super().add(
            client, offset_to_current=self.current_offset, client_position=self.current_position
        )

    def configure(self, client, screen_rect):
        pass

    cmd_previous = _SimpleLayoutBase.previous
    cmd_next = _SimpleLayoutBase.next

    cmd_up = cmd_previous
    cmd_down = cmd_next


class BaseLayoutConfigBottom(Config):
    auto_fullscreen = True
    groups = [libqtile.config.Group("a")]
    layouts = [DummyLayout(current_position="bottom")]
    floating_layout = libqtile.resources.default_config.floating_layout
    keys = []
    mouse = []
    screens = []


class BaseLayoutConfigTop(Config):
    auto_fullscreen = True
    groups = [libqtile.config.Group("a")]
    layouts = [DummyLayout(current_position="top")]
    floating_layout = libqtile.resources.default_config.floating_layout
    keys = []
    mouse = []
    screens = []


baselayoutconfigbottom = pytest.mark.parametrize(
    "manager", [BaseLayoutConfigBottom], indirect=True
)
baselayoutconfigtop = pytest.mark.parametrize("manager", [BaseLayoutConfigTop], indirect=True)


@baselayoutconfigbottom
def test_base_client_position_bottom(manager):
    manager.test_window("one")
    manager.test_window("two")
    assert manager.c.layout.info()["clients"] == ["one", "two"]


@baselayoutconfigtop
def test_base_client_position_top(manager):
    manager.test_window("one")
    manager.test_window("two")
    assert manager.c.layout.info()["clients"] == ["two", "one"]
