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

class Dmenu():
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
        ("height", None, "defines the height"),
    ]

    args = []

    def __init__(self, config):
        default_config = dict((d[0], d[1]) for d in self.defaults)
        default_config.update(config)
        self.configure(config)


    def configure(self, config):
        if 'bottom' in config and config['bottom']:
            self.args.append("-b")
        if 'ignorecase' in config and config['ignorecase']:
            self.args.append("-i")
        if 'lines' in config and config['lines']:
            self.args.extend(("-l", str(config['lines'])))
        if 'prompt' in config and config['prompt']:
            self.args.extend(("-p", config['prompt']))
        if 'font' in config and config['font']:
            self.args.extend(("-fn", config['font']))
        if 'background' in config and config['background']:
            self.args.extend(("-nb", config['background']))
        if 'foreground' in config and config['foreground']:
            self.args.extend(("-nf", config['foreground']))
        if 'selected_background' in config and config['selected_background']:
            self.args.extend(("-sb", config['selected_background']))
        if 'selected_foreground' in config and config['selected_foreground']:
            self.args.extend(("-sf", config['selected_foreground']))
        if 'height' in config and config['height']:
            self.args.extend(("-h", str(config['height'])))


    def call(self, items=[]):
        input_str = six.b("\n".join([str(i) for i in items]) + "\n")
        proc = Popen(["dmenu"] + self.args, stdout=PIPE, stdin=PIPE)
        return proc.communicate(input_str)[0]


    def run_apps(self):
        proc = Popen(["dmenu_run"] + self.args, stdout=PIPE, stdin=PIPE)



class DmenuRun():
    """
    Special case to run applications.
    """
    config = {}

    def __init__(self, qtile):
        if hasattr(qtile.config, 'extentions') and qtile.config.extentions['dmenu']:
            self.config = qtile.config.extentions['dmenu']


    def run(self):
        dmenu = Dmenu(self.config)
        dmenu.run_apps()
        del dmenu
