import pytest

import libqtile.bar
import libqtile.config
import libqtile.confreader
import libqtile.layout
from libqtile import widget

sep = widget.Sep()

parameters = [
    (libqtile.config.Screen(top=libqtile.bar.Bar([sep], 10)), "top", "width"),
    (libqtile.config.Screen(left=libqtile.bar.Bar([sep], 10)), "left", "height"),
]


@pytest.mark.parametrize("screen,location,attribute", parameters)
def test_orientations(manager_nospawn, minimal_conf_noscreen, screen, location, attribute):
    config = minimal_conf_noscreen
    config.screens = [screen]

    manager_nospawn.start(config)
    bar = manager_nospawn.c.bar[location]

    w = bar.info()["widgets"][0]
    assert w[attribute] == 3


def test_padding_and_width(manager_nospawn, minimal_conf_noscreen):
    sep = widget.Sep(padding=5, linewidth=7)

    config = minimal_conf_noscreen
    config.screens = [libqtile.config.Screen(top=libqtile.bar.Bar([sep], 10))]

    manager_nospawn.start(config)
    topbar = manager_nospawn.c.bar["top"]

    w = topbar.info()["widgets"][0]
    assert w["width"] == 12


def test_deprecated_config():
    sep = widget.Sep(height_percent=80)
    assert sep.size_percent == 80
