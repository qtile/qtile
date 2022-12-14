# Copyright (c) 2022 Egor Martynov
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

import os

from libqtile.log_utils import logger
from libqtile.widget import base


class YandexDisk(base.InLoopPollText):
    """A simple widget to show YandexDisk client folder sync status.

    Yandex.Disk_ is a service that lets you store files on Yandex servers.

    .. _Yandex.Disk: http://disk.yandex.com/

    """

    defaults = [
        ("sync_folder", "~/Yandex.Disk/", "Yandex.Disk folder path"),
        ("update_interval", 10, "The delay in seconds between updates"),
        ("format", "{status}", "Display format"),
    ]

    def __init__(self, **config):
        base.InLoopPollText.__init__(self, **config)
        self.add_defaults(YandexDisk.defaults)

        self.sync_folder = os.path.expanduser(
            os.path.join(
                self.sync_folder,
                ".sync",
                "status",
            )
        )

    def _get_status(self):
        with open(self.sync_folder, "r") as file:
            return file.read().split("\n")[-1]

    def poll(self):
        try:
            status = self._get_status()
        except Exception:
            logger.exception("Error getting status for yandex.disk")
            return "Error"

        return self.format.format(status=status)
