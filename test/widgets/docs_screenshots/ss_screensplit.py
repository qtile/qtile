import pytest

import libqtile.config
import libqtile.confreader
import libqtile.layout
import libqtile.resources.default_config
from libqtile.widget import ScreenSplit


@pytest.fixture
def widget():
    yield ScreenSplit


# We need to override default minimal_conf so we can force the layout
@pytest.fixture(scope="function")
def minimal_conf_noscreen():
    class MinimalConf(libqtile.confreader.Config):
        auto_fullscreen = False
        keys = []
        mouse = []
        groups = [libqtile.config.Group("a"), libqtile.config.Group("b")]
        layouts = [libqtile.layout.ScreenSplit()]
        floating_layout = libqtile.resources.default_config.floating_layout
        screens = []

    return MinimalConf


def ss_screensplit(screenshot_manager):
    screenshot_manager.take_screenshot()
