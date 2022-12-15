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
import shlex

from libqtile.log_utils import logger
from libqtile.widget import base

status_mapping = {
    "idle": "IDLE",
    "stopped": "STOPPED",
    "paused": "PAUSED",
    "busy": "BUSY",
    "index": "INDEX",
}


class YandexDisk(base.InLoopPollText):
    """A simple widget to show YandexDisk client folder sync status.

    Yandex.Disk_ is a cloud service created by Yandex that lets users store
    files on "cloud" servers and share them with others online.
    The service is based on syncing data between different devices.

    .. _Yandex.Disk: http://disk.yandex.com/

    """

    defaults = [
        ("sync_folder", "~/Yandex.Disk/", "Yandex.Disk folder path"),
        ("status_mapping", status_mapping, "Sync status mapping"),
        ("update_interval", 5, "The delay in seconds between updates"),
        ("format", "{status}{progress}", "Display format"),
        ("progress_format", " ({filename} {percentage:.1%})", "Progress format"),
    ]

    def __init__(self, **config):
        base.InLoopPollText.__init__(self, **config)
        self.add_defaults(YandexDisk.defaults)

        self.sync_folder = os.path.expanduser(
            os.path.join(
                self.sync_folder,
                ".sync",
            )
        )

        self.status_file = os.path.join(self.sync_folder, "status")
        self.core_log_file = os.path.join(self.sync_folder, "core.log")

    def _get_status(self):
        with open(self.status_file, "r") as file:
            status = file.read().split("\n")[-1]
            return status

    def _get_latest_log(self):
        with open(self.core_log_file, "r") as file:
            latest_log = file.read().split("\n")[-2]
            log_line = shlex.split(latest_log)
            if log_line:
                log_time = log_line.pop(0)
                log_type = log_line.pop(0)
                log_data = log_line
                return log_time, log_type, log_data

    def poll(self):
        try:
            status = self._get_status()
        except FileNotFoundError:
            status = "stopped"
        except Exception:
            logger.exception("Error getting status for yandex.disk")
            return "Error"

        progress = ""

        try:
            if status in ["busy", "index"]:
                log = self._get_latest_log()
                if log:
                    _, log_type, log_data = log
                    if log_type in ["DIGEST", "PUT"]:
                        keys = self._get_progress_log_dict(log_data)
                        progress = self.progress_format.format(**keys)
        except FileNotFoundError:
            pass
        except Exception:
            logger.exception("Error getting information from core.log for yandex.disk")
            return "Error"

        status = self.status_mapping.get(status, status)

        return self.format.format(status=status, progress=progress)

    @staticmethod
    def _get_progress_log_dict(log_data):

        if len(log_data) == 4:
            synced_size = int(log_data[1])
            total_size = int(log_data[3])

            return {
                "filename": log_data[0],
                "synced_size": synced_size,
                "total_size": total_size,
                "percentage": synced_size / total_size,
            }
