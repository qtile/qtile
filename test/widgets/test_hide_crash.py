import pytest

from libqtile import bar
from libqtile.config import Screen
from libqtile.confreader import Config
from libqtile.widget.base import _Widget


class BadWidget(_Widget):
    def __init__(self, **config):
        _Widget.__init__(self, bar.CALCULATED, **config)

    def _configure(self, qtile, bar):
        _Widget._configure(self, qtile, bar)
        # Crash!
        1 / 0


class CrashConfig(Config):
    screens = [Screen(top=bar.Bar([BadWidget(), BadWidget(hide_crash=True)], 20))]


crash_config = pytest.mark.parametrize("manager", [CrashConfig], indirect=True)


@crash_config
def test_hide_crashed_widget(manager):
    widgets = manager.c.bar["top"].items("widget")[1]
    # There should only be one widget in the bar
    assert len(widgets) == 1

    # That widget should be a ConfigErrorWidget
    assert widgets[0] == "configerrorwidget"
