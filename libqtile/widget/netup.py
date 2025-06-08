# Copyright (c) 2025 e-devnull
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

from subprocess import DEVNULL, run

from libqtile.log_utils import logger
from libqtile.widget import base


class NetUP(base.ThreadPoolText):
    """
    A widget to display whether the network connection is up or down by pinging a host.

    By default ``host`` parameter is set to ``None``.
    """

    defaults = [
        ("host", None, "Host to ping."),
        ("update_interval", 30, "Update interval in seconds."),
        ("display_fmt", "NET {0}", "Display format."),
        ("up_foreground", "FFFFFF", "Font color on up."),
        ("down_foreground", "FF0000", "Font color on down."),
    ]

    def __init__(self, **config):
        base.ThreadPoolText.__init__(self, config.pop("initial_text", "NET ?"), **config)
        self.add_defaults(NetUP.defaults)
        if not self.host:
            logger.error("You need to specify a host to ping.")

    def poll(self):
        if not self.host:
            return "NET ?"
        else:
            process = run(["ping", "-c", "1", self.host], stdout=DEVNULL, stderr=DEVNULL)
            if process.returncode == 0:
                self.layout.colour = self.up_foreground
                return self.display_fmt.format("up")
            self.layout.colour = self.down_foreground
            return self.display_fmt.format("down")
