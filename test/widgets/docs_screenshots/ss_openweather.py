import pytest

from libqtile.widget.textbox import TextBox


@pytest.fixture
def widget():
    yield TextBox


@pytest.mark.parametrize(
    "screenshot_manager,expected",
    [
        ({}, "London: 7.0 °C 81% light intensity drizzle"),
        ({}, "London: 07:40 16:47"),
        ({}, "London: 4.1 80 E"),
        ({}, "London: 🌧️"),
    ],
    indirect=["screenshot_manager"],
)
def ss_openweather(screenshot_manager, expected):
    screenshot_manager.c.widget["textbox"].update(expected)
    screenshot_manager.take_screenshot()
