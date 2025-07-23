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

import socket
from subprocess import DEVNULL, run

from libqtile.log_utils import logger
from libqtile.widget import base


class NetUP(base.BackgroundPoll):
    """
    A widget to display whether the network connection is up or down by probing a host via ping
    or tcp connection.

    By default ``host`` parameter is set to ``None``.
    """

    defaults = [
        ("host", None, "Host to probe."),
        ("method", "ping", "tcp or ping."),
        ("port", 443, "TCP port."),
        ("update_interval", 30, "Update interval in seconds."),
        ("display_fmt", "NET {0}", "Display format."),
        ("up_foreground", "FFFFFF", "Font color when host is up."),
        ("down_foreground", "FF0000", "Font color when host is down."),
        ("up_string", "up", "String to display when host is up."),
        ("down_string", "down", "String to display when host is down."),
    ]

    def __init__(self, **config):
        base.BackgroundPoll.__init__(self, **config)
        self.add_defaults(NetUP.defaults)

    def is_host_empty(self):
        if not self.host:
            logger.error("Host is not set")
            return False
        return True

    def validate_method(self):
        if self.method == "ping" or self.method == "tcp":
            return True
        logger.error("Method is invalid")
        return False

    def validate_port(self):
        if not isinstance(self.port, int):
            logger.error("Port is invalid")
            return False
        if self.port >= 1 and self.port <= 65535:
            return True
        else:
            logger.error("Port is invalid")
            return False

    def check_ping(self):
        process = run(["ping", "-c", "1", self.host], stdout=DEVNULL, stderr=DEVNULL)
        return process.returncode

    def check_tcp(self):
        sc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sc.settimeout(1)
        try:
            returncode = sc.connect_ex((self.host, self.port))
        except OSError:
            returncode = -1
        finally:
            sc.close()
        return returncode

    def is_up(self):
        if self.method == "ping":
            if self.check_ping() == 0:
                return True
            return False
        if self.method == "tcp":
            if self.check_tcp() == 0:
                return True
            return False

    def poll(self):
        if (
            not self.is_host_empty()
            or not self.validate_method()
            or (self.method == "tcp" and not self.validate_port())
        ):
            return "N/A"

        if self.is_up():
            self.layout.colour = self.up_foreground
            return self.display_fmt.format(self.up_string)
        self.layout.colour = self.down_foreground
        return self.display_fmt.format(self.down_string)
