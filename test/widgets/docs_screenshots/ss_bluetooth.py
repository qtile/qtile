import pytest

from test.widgets.test_bluetooth import fake_dbus_daemon, wait_for_text, widget  # noqa: F401


@pytest.mark.parametrize(
    "screenshot_manager",
    [
        {},
    ],
    indirect=True,
)
def ss_bluetooth(fake_dbus_daemon, screenshot_manager):  # noqa: F811
    w = screenshot_manager.c.widget["bluetooth"]
    wait_for_text(w, "BT Speaker")
    screenshot_manager.take_screenshot()

    for _ in range(4):
        w.scroll_up()
        screenshot_manager.take_screenshot()
