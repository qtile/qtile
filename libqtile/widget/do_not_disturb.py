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

from libqtile.lazy import lazy
from libqtile.log_utils import logger
from libqtile.widget import base


class DoNotDisturb(base.InLoopPollText):
    """
    Displays Do Not Disturb status for notification server Dunst by default.
    Can be used with other servers by changing the poll command and mouse callbacks.
    """

    defaults = [
        (
            "poll_function",
            None,
            "Function that returns the notification server status. "
            "Define the function on your configuration file and "
            "pass it like poll_function=my_func. "
            "Must return either true or false",
        ),
        ("enabled_icon", "X", "Icon that displays when do not disturb is enabled"),
        ("disabled_icon", "O", "Icon that displays when do not disturb is disabled"),
        ("update_interval", 1, "How often in seconds the text must update"),
    ]

    def __init__(self, **config):
        base.InLoopPollText.__init__(self, **config)
        self.add_defaults(DoNotDisturb.defaults)
        self.status_retrieved_error = False
        if self.poll_function is None:
            self.add_callbacks(
                {
                    "Button1": lazy.spawn("dunstctl set-paused toggle"),
                    "Button3": lazy.spawn("dunstctl history-pop"),
                }
            )

    def dunst_status(self):
        status = check_output(["dunstctl", "is-paused"]).strip()
        if status == b"true":
            return True
        return False

    def poll(self):
        check = None
        if self.poll_function is None:
            check = self.dunst_status()
        elif callable(self.poll_function):
            check = self.poll_function()
        else:
            if not self.status_retrieved_error:
                logger.error("Custom poll function cannot be called")
                self.status_retrieved_error = True
        if check:
            return self.enabled_icon
        else:
            return self.disabled_icon
