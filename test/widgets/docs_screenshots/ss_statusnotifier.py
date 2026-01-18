import pytest

from libqtile.widget import StatusNotifier
from test.widgets.test_statusnotifier import wait_for_icon


@pytest.fixture
def widget(request, manager_nospawn):
    yield StatusNotifier


@pytest.mark.parametrize("screenshot_manager", [{}, {"icon_size": 30}], indirect=True)
@pytest.mark.usefixtures("dbus")
def ss_statusnotifier(screenshot_manager):
    win = screenshot_manager.test_window("TestSNI", export_sni=True)
    wait_for_icon(screenshot_manager.c.widget["statusnotifier"], hidden=False)

    screenshot_manager.take_screenshot()
    screenshot_manager.kill_window(win)
