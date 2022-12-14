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
import tempfile

import pytest

from libqtile import widget


@pytest.fixture
def yandexdisk_folder():
    with tempfile.TemporaryDirectory() as tmp:
        sync_folder = os.path.join(tmp, "Yandex.Disk")

        status_file = os.path.join(sync_folder, ".sync", "status")
        os.makedirs(os.path.dirname(status_file), exist_ok=True)

        with open(status_file, "w") as f:
            f.write("99999\nidle")

        yield sync_folder


def test_yandexdisk_idle(yandexdisk_folder):
    yandexdisk = widget.YandexDisk(sync_folder=yandexdisk_folder)
    assert yandexdisk.poll() == "idle"


def test_yandexdisk_stopped(yandexdisk_folder):
    yandexdisk = widget.YandexDisk(sync_folder=yandexdisk_folder, daemon_stopped="stopped")
    assert yandexdisk.daemon_stopped == "stopped"

    status_file = os.path.join(yandexdisk_folder, ".sync", "status")
    os.remove(status_file)

    assert yandexdisk.poll() == yandexdisk.daemon_stopped
