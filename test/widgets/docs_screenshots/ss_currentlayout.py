import pytest

from libqtile.widget import CurrentLayout
from test.widgets.docs_screenshots.conftest import widget_config


@pytest.fixture
def widget(monkeypatch):
    yield CurrentLayout


@widget_config(
    [
        {},
        {"mode": "icon"},
        {"mode": "both", "icon_first": False},
        {"mode": "both", "icon_first": True},
    ]
)
def ss_currentlayout(screenshot_manager):
    screenshot_manager.take_screenshot()
