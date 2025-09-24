import pytest

from libqtile import config, widget
from libqtile.bar import Bar
from test.helpers import BareConfig


class GroupBoxConfig(BareConfig):
    screens = [
        config.Screen(
            top=Bar([widget.GroupBox(), widget.GroupBox(name="has_markup", markup=True)], 24)
        )
    ]
    groups = [config.Group("1", label="<sup>1</sup>")]


groupbox_config = pytest.mark.parametrize("manager", [GroupBoxConfig], indirect=True)


@groupbox_config
def test_groupbox_markup(manager):
    """Group labels can support markup but this is disabled by default."""
    no_markup = manager.c.widget["groupbox"]
    has_markup = manager.c.widget["has_markup"]

    # If markup is disabled, text will include markup tags so widget will be wider
    assert no_markup.info()["width"] > has_markup.info()["width"]
