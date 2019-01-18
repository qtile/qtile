# Copyright (c) 2011 Florian Mounier
# Copyright (c) 2014 Sean Vig
# Copyright (c) 2014 Tycho Andersen
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

import os
import pytest

from libqtile import confreader
from libqtile import config, utils
from libqtile.core import xcore

tests_dir = os.path.dirname(os.path.realpath(__file__))


def test_validate():
    xc = xcore.XCore()
    f = confreader.Config.from_file(xc, os.path.join(tests_dir, "configs", "basic.py"))
    f.validate(xc)
    f.keys[0].key = "nonexistent"
    with pytest.raises(confreader.ConfigError):
        f.validate(xc)

    f.keys[0].key = "x"
    f = confreader.Config.from_file(xc, os.path.join(tests_dir, "configs", "basic.py"))
    f.keys[0].modifiers = ["nonexistent"]
    with pytest.raises(confreader.ConfigError):
        f.validate(xc)
    f.keys[0].modifiers = ["shift"]


def test_syntaxerr():
    xc = xcore.XCore()
    with pytest.raises(confreader.ConfigError):
        confreader.Config.from_file(xc, os.path.join(tests_dir, "configs", "syntaxerr.py"))


def test_basic():
    xc = xcore.XCore()
    f = confreader.Config.from_file(xc, os.path.join(tests_dir, "configs", "basic.py"))
    assert f.keys


def test_falls_back():
    xc = xcore.XCore()
    f = confreader.Config.from_file(xc, os.path.join(tests_dir, "configs", "basic.py"))

    # We just care that it has a default, we don't actually care what the
    # default is; don't assert anything at all about the default in case
    # someone changes it down the road.
    assert hasattr(f, "follow_mouse_focus")


def test_ezkey():

    def cmd(x):
        return None

    key = config.EzKey('M-A-S-a', cmd, cmd)
    modkey, altkey = (config.EzConfig.modifier_keys[i] for i in 'MA')
    assert key.modifiers == [modkey, altkey, 'shift']
    assert key.key == 'a'
    assert key.commands == (cmd, cmd)

    key = config.EzKey('M-<Tab>', cmd)
    assert key.modifiers == [modkey]
    assert key.key == 'Tab'
    assert key.commands == (cmd,)

    with pytest.raises(utils.QtileError):
        config.EzKey('M--', cmd)

    with pytest.raises(utils.QtileError):
        config.EzKey('Z-Z-z', cmd)

    with pytest.raises(utils.QtileError):
        config.EzKey('asdf', cmd)

    with pytest.raises(utils.QtileError):
        config.EzKey('M-a-A', cmd)


def test_ezclick_ezdrag():

    def cmd(x):
        return None

    btn = config.EzClick('M-1', cmd)
    assert btn.button == 'Button1'
    assert btn.modifiers == [config.EzClick.modifier_keys['M']]

    btn = config.EzDrag('A-2', cmd)
    assert btn.button == 'Button2'
    assert btn.modifiers == [config.EzClick.modifier_keys['A']]
