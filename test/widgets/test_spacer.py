import pytest

import libqtile.bar
import libqtile.config
import libqtile.confreader
import libqtile.layout
from libqtile import widget

space = widget.Spacer()

parameters = [
    (libqtile.config.Screen(top=libqtile.bar.Bar([space], 10)), "top", "width"),
    (libqtile.config.Screen(left=libqtile.bar.Bar([space], 10)), "left", "height"),
]


@pytest.mark.parametrize("screen,location,attribute", parameters)
def test_stretch(manager_nospawn, minimal_conf_noscreen, screen, location, attribute):
    config = minimal_conf_noscreen
    config.screens = [screen]

    manager_nospawn.start(config)
    bar = manager_nospawn.c.bar[location]

    info = bar.info()
    assert info["widgets"][0][attribute] == info[attribute]


space = widget.Spacer(length=100)
parameters = [
    (libqtile.config.Screen(top=libqtile.bar.Bar([space], 10)), "top", "width"),
    (libqtile.config.Screen(left=libqtile.bar.Bar([space], 10)), "left", "height"),
]


@pytest.mark.parametrize("screen,location,attribute", parameters)
def test_fixed_size(manager_nospawn, minimal_conf_noscreen, screen, location, attribute):
    config = minimal_conf_noscreen
    config.screens = [screen]

    manager_nospawn.start(config)
    bar = manager_nospawn.c.bar[location]

    info = bar.info()
    assert info["widgets"][0][attribute] == 100
