import os
import shutil

import pytest

from libqtile.widget import Volume
from test.widgets.conftest import DATA_DIR

ICON = os.path.join(DATA_DIR, "svg", "audio-volume-muted.svg")
TEMP_DIR = os.path.join(DATA_DIR, "ss_temp")


@pytest.fixture
def widget():
    os.mkdir(TEMP_DIR)
    for i in (
        "audio-volume-high.svg",
        "audio-volume-low.svg",
        "audio-volume-medium.svg",
        "audio-volume-muted.svg",
    ):
        shutil.copy(ICON, os.path.join(TEMP_DIR, i))

    yield Volume

    shutil.rmtree(TEMP_DIR)


@pytest.mark.parametrize(
    "screenshot_manager",
    [{"theme_path": TEMP_DIR}, {"emoji": True}, {"fmt": "Vol: {}"}],
    indirect=True,
)
def ss_volume(screenshot_manager):
    widget = screenshot_manager.c.widget["volume"]
    widget.eval("self.volume=-1")
    widget.eval("self._update_drawer()")
    widget.eval("self.bar.draw()")
    screenshot_manager.take_screenshot()
