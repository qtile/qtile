import shutil
import subprocess

import pytest

from libqtile.widget import Notify
from test.widgets.test_notify import NS, notification

_, NOTIFICATION = notification("Notification", "Message body.")


@pytest.fixture
def widget():
    yield Notify


@pytest.mark.parametrize(
    "screenshot_manager",
    [
        {},
    ],
    indirect=True,
)
@pytest.mark.skipif(shutil.which("notify-send") is None, reason="notify-send not installed.")
@pytest.mark.usefixtures("dbus")
def ss_notify(screenshot_manager):
    notif_1 = [NS]
    notif_1.extend(NOTIFICATION)
    subprocess.run(notif_1)
    screenshot_manager.take_screenshot()
