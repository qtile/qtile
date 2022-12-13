import os

from libqtile import widget

import pytest


@pytest.fixture
def yandexdisk_folder():
    tmp = "/var/tmp/qtile/test/widgets/yandexdisk"
    sync_folder = os.path.join(tmp, "Yandex.Disk")

    status_file = os.path.join(sync_folder, ".sync", "status")
    os.makedirs(os.path.dirname(status_file), exist_ok=True)

    with open(status_file, "w") as f:
        f.write("99999\nidle")

    yield sync_folder


def test_yandexdisk(yandexdisk_folder):
    YandexDisk = widget.YandexDisk(sync_folder=yandexdisk_folder)
    assert YandexDisk.poll() == "idle"
