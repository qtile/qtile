import pytest

from libqtile.widget import GroupBox


@pytest.fixture
def widget():
    yield GroupBox


@pytest.mark.parametrize(
    "screenshot_manager",
    [
        {},
        {"highlight_method": "block"},
        {"highlight_method": "text"},
        {"highlight_method": "line"},
        {"visible_groups": ["1", "5", "6"]},
    ],
    indirect=True,
)
def ss_groupbox(screenshot_manager):
    screenshot_manager.test_window("One")
    screenshot_manager.take_screenshot()
