# Copyright (c) 2008, 2010 Aldo Cortesi
# Copyright (c) 2011 Mounier Florian
# Copyright (c) 2012, 2015 Tycho Andersen
# Copyright (c) 2013 Tao Sauvage
# Copyright (c) 2013 Craig Barnes
# Copyright (c) 2014 Sean Vig
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

from typing import Any, List, Tuple

from .. import bar
from . import base


class TextBox(base._TextBox):
    """A flexible textbox that can be updated from bound keys, scripts, and qshell

    Callback functions can be assigned to button presses by passing a dict to the
    'callbacks' kwarg. For example: {'Button1': func} will execute func when the widget
    receives a button 1 press. The Qtile instance of passed as the only argument to the
    callback functions.

    """
    orientations = base.ORIENTATION_HORIZONTAL
    defaults = [
        ("font", "sans", "Text font"),
        ("fontsize", None, "Font pixel size. Calculated if None."),
        ("fontshadow", None, "font shadow color, default is None(no shadow)"),
        ("padding", None, "Padding left and right. Calculated if None."),
        ("foreground", "#ffffff", "Foreground colour."),
        ("mouse_callbacks", {}, "Dict of mouse button press callback functions."),
    ]  # type: List[Tuple[str, Any, str]]

    def __init__(self, text=" ", width=bar.CALCULATED, **config):
        base._TextBox.__init__(self, text=text, width=width, **config)

    def update(self, text):
        self.text = text
        self.bar.draw()

    def button_press(self, x, y, button):
        name = 'Button{0}'.format(button)
        if name in self.mouse_callbacks:
            self.mouse_callbacks[name](self.qtile)

    def cmd_update(self, text):
        """Update the text in a TextBox widget"""
        self.update(text)

    def cmd_get(self):
        """Retrieve the text in a TextBox widget"""
        return self.text
