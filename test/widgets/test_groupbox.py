# Copyright (c) 2024 elParaguayo
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

from libqtile import config, widget
from libqtile.bar import Bar
from test.helpers import BareConfig


class GroupBoxConfig(BareConfig):
    screens = [
        config.Screen(
            top=Bar([widget.GroupBox(), widget.GroupBox(name="has_markup", markup=True)], 24)
        )
    ]
    groups = [config.Group("1", label="<sup>1</sup>")]


groupbox_config = pytest.mark.parametrize("manager", [GroupBoxConfig], indirect=True)


@groupbox_config
def test_groupbox_markup(manager):
    """Group labels can support markup but this is disabled by default."""
    no_markup = manager.c.widget["groupbox"]
    has_markup = manager.c.widget["has_markup"]

    # If markup is disabled, text will include markup tags so widget will be wider
    assert no_markup.info()["width"] > has_markup.info()["width"]
