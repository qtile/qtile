# Copyright (c) 2015 Tycho Andersen
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

# Widget specific tests

import pytest

from libqtile.bar import Bar
from libqtile.command.base import expose_command
from libqtile.config import Screen
from libqtile.widget import TextBox
from test.conftest import BareConfig


class ColorChanger(TextBox):
    count = 0

    @expose_command()
    def update(self, text):
        self.count += 1
        if self.count % 2 == 0:
            self.foreground = "ff0000"
        else:
            self.foreground = "0000ff"
        self.text = text


class WidgetTestConf(BareConfig):
    screens = [Screen(bottom=Bar([ColorChanger(name="colorchanger")], 20))]


widget_conf = pytest.mark.parametrize("manager", [WidgetTestConf], indirect=True)


@widget_conf
def test_textbox_color_change(manager):
    widget = manager.c.widget["colorchanger"]

    widget.update("f")
    assert widget.eval("self.foreground")[1] == "0000ff"

    widget.update("f")
    assert widget.eval("self.foreground")[1] == "ff0000"
