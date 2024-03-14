# Copyright (c) 2024 Sprinter05
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

from subprocess import check_output

from libqtile.log_utils import logger
from libqtile.widget import base
from libqtile.lazy import lazy

class DoNotDisturb(base.InLoopPollText):
    """
    Displays Do Not Disturb status for notification server Dunst by default.
    Can be used with other servers by changing the poll command and mouse callbacks.
    """

    orientations = base.ORIENTATION_HORIZONTAL
    defaults = [
        (
            "poll_function",
            None,
            "Function that returns the notification server status"
            "e.g def func():"
            "       return true"
            "Must return either true or false",
        ),
        ("enabled_icon", "X", "Icon that displays when do not disturb is enabled"),
        ("disabled_icon", "O", "Icon that displays when do not disturb is disabled"),
        ("update_interval", 1, "How often in seconds the text must update")
    ]

    def __init__(self, **config):
        base.InLoopPollText.__init__(self, **config)
        self.add_defaults(DoNotDisturb.defaults)
