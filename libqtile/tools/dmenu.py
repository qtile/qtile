# Copyright (C) 2016, zordsdavini
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

import six
from subprocess import Popen, PIPE

from .. import configurable

class Dmenu(configurable.Configurable):
    """
    Python wrapper for dmenu
    http://tools.suckless.org/dmenu/
    """
    defaults = [
        ("bottom", False, "dmenu appears at the bottom of the screen"),
        ("ignorecase", False, "dmenu matches menu items case insensitively"),
        ("lines", None, "dmenu lists items vertically, with the given number of lines"),
        ("prompt", None, "defines the prompt to be displayed to the left of the input field"),
        ("font", None, "defines the font or font set used"),
        ("background", None, "defines  the normal background color"),
        ("foreground", None, "defines the normal foreground color"),
        ("selected_background", None, "defines the selected background color"),
        ("selected_foreground", None, "defines the selected foreground color"),
    ]

    args = ["dmenu"]

    def __init__(self, **config):
        configurable.Configurable.__init__(self, **config)
        self.add_defaults(Dmenu.defaults)
        self.configure()

    def configure(self):
        if self.bottom:
            self.args.append("-b")
        if self.ignorecase:
            self.args.append("-i")
        if self.lines:
            self.args.extend(("-l", str(self.lines)))
        if self.prompt:
            self.args.extend(("-p", self.prompt))
        if self.font:
            self.args.extend(("-fn", self.font))
        if self.background:
            self.args.extend(("-nb", self.background))
        if self.foreground:
            self.args.extend(("-nf", self.foreground))
        if self.selected_background:
            self.args.extend(("-sb", self.selected_background))
        if self.selected_foreground:
            self.args.extend(("-sf", self.selected_foreground))

    def run(self, items):
        input_str = six.b("\n".join([str(i) for i in items]) + "\n")
        proc = Popen(self.args, stdout=PIPE, stdin=PIPE)
        return proc.communicate(input_str)[0]
