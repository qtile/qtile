import pytest

from libqtile.widget import yandexdisk
from test.widgets.test_yandexdisk import yandexdisk_folder


@pytest.fixture
def widget(monkeypatch):
    monkeypatch.setattr("libqtile.widget.yandexdisk.YandexDisk.sync_folder", yandexdisk_folder)
    yield yandexdisk.YandexDisk


@pytest.mark.parametrize("screenshot_manager", indirect=True)
def ss_yandexdisk(screenshot_manager):
    screenshot_manager.take_screenshot()
