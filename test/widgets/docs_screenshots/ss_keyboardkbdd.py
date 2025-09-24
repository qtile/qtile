from importlib import reload

import pytest

from test.widgets.test_keyboardkbdd import MockSpawn, mock_signal_receiver


@pytest.fixture
def widget(monkeypatch):
    from libqtile.widget import keyboardkbdd

    reload(keyboardkbdd)
    monkeypatch.setattr(
        "libqtile.widget.keyboardkbdd.KeyboardKbdd.call_process", MockSpawn.call_process
    )
    monkeypatch.setattr("libqtile.widget.keyboardkbdd.add_signal_receiver", mock_signal_receiver)
    return keyboardkbdd.KeyboardKbdd


@pytest.mark.parametrize(
    "screenshot_manager", [{"configured_keyboards": ["gb", "us"]}], indirect=True
)
def ss_keyboardkbdd(screenshot_manager):
    screenshot_manager.take_screenshot()
