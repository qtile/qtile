import pytest

import libqtile.widget
from test.widgets.test_df import FakeOS


@pytest.fixture
def widget(monkeypatch):
    monkeypatch.setattr("libqtile.widget.df.os", FakeOS("os"))
    yield libqtile.widget.DF


@pytest.mark.parametrize(
    "screenshot_manager",
    [{"warn_space": 40}, {"visible_on_warn": False}],
    indirect=True,
)
def ss_df(screenshot_manager):
    screenshot_manager.take_screenshot()
