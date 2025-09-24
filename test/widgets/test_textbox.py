import pytest

import libqtile.bar
import libqtile.config
from libqtile import widget


@pytest.mark.parametrize("position", ["top", "bottom", "left", "right"])
def test_text_box_bar_orientations(manager_nospawn, minimal_conf_noscreen, position):
    """Text boxes are available on any bar position."""
    textbox = widget.TextBox(text="Testing")

    config = minimal_conf_noscreen
    config.screens = [libqtile.config.Screen(**{position: libqtile.bar.Bar([textbox], 10)})]

    manager_nospawn.start(config)
    tbox = manager_nospawn.c.widget["textbox"]

    assert tbox.info()["text"] == "Testing"

    tbox.update("Updated")
    assert tbox.info()["text"] == "Updated"


def test_text_box_max_chars(manager_nospawn, minimal_conf_noscreen):
    """Text boxes are available on any bar position."""
    textbox = widget.TextBox(text="Testing", max_chars=4)

    config = minimal_conf_noscreen
    config.screens = [libqtile.config.Screen(top=libqtile.bar.Bar([textbox], 10))]

    manager_nospawn.start(config)
    tbox = manager_nospawn.c.widget["textbox"]

    assert tbox.info()["text"] == "Test…"
