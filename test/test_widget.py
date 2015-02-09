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

from libqtile.config import Screen
from libqtile.bar import Bar
from libqtile.widget import TextBox

from .utils import Xephyr
from .test_manager import BareConfig

class ColorChanger(TextBox):
    count = 0
    def update(self, text):
        self.count += 1
        if self.count % 2 == 0:
            self.foreground = "ff0000"
        else:
            self.foreground = "0000ff"
        self.text = text

class WidgetTestConf(BareConfig):
    screens = [Screen(bottom=Bar([ColorChanger(name="colorchanger")], 20))]

@Xephyr(False, WidgetTestConf())
def test_textbox_color_change(self):
    self.c.widget["colorchanger"].update('f')
    print(self.c.widget["colorchanger"].info())
    assert self.c.widget["colorchanger"].info()["foreground"] == "0000ff"

    self.c.widget["colorchanger"].update('f')
    assert self.c.widget["colorchanger"].info()["foreground"] == "ff0000"
