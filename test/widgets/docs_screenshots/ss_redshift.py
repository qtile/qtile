import pytest

import libqtile.widget
from test.widgets.test_redshift import mock_run


@pytest.fixture
def widget(monkeypatch):
    monkeypatch.setattr("subprocess.run", mock_run)
    yield libqtile.widget.redshift.Redshift


@pytest.mark.parametrize(
    "screenshot_manager",
    [
        {},
    ],
    indirect=True,
)
def ss_redshift(screenshot_manager):
    def click():
        screenshot_manager.c.bar["top"].fake_button_press(0, 0, 1)

    w = screenshot_manager.c.widget["redshift"]

    screenshot_manager.take_screenshot()

    click()  # Enable so scrolling works

    number_of_items = 4
    for _ in range(number_of_items):
        screenshot_manager.take_screenshot()
        w.scroll_up()
