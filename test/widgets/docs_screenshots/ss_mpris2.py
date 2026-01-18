import pytest

from test.widgets.test_mpris2widget import (  # noqa: F401
    METADATA_PAUSED,
    METADATA_PLAYING,
    patched_module,
)


@pytest.fixture
def widget(monkeypatch, patched_module):  # noqa: F811
    patched_module.Mpris2.PLAYING = METADATA_PLAYING
    patched_module.Mpris2.PAUSED = METADATA_PAUSED
    return patched_module.Mpris2


@pytest.mark.parametrize(
    "screenshot_manager",
    [{}, {"scroll_chars": 45}, {"display_metadata": ["xesam:url"]}],
    indirect=True,
)
def ss_mpris2(screenshot_manager):
    widget = screenshot_manager.c.widget["mpris2"]
    widget.eval("self.parse_message(*self.PLAYING.body)")
    screenshot_manager.take_screenshot()


@pytest.mark.parametrize(
    "screenshot_manager", [{"stop_pause_text": "Player paused"}], indirect=True
)
def ss_mpris2_paused(screenshot_manager):
    widget = screenshot_manager.c.widget["mpris2"]
    widget.eval("self.parse_message(*self.PAUSED.body)")
    screenshot_manager.take_screenshot()
