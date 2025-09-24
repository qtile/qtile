import libqtile.bar
import libqtile.config
import libqtile.confreader
import libqtile.layout
from libqtile import widget
from libqtile.lazy import lazy


def test_lazy_callback(manager_nospawn, minimal_conf_noscreen):
    """Test widgets accept lazy calls"""
    textbox = widget.TextBox(
        text="Testing",
        mouse_callbacks={
            "Button1": lazy.widget["textbox"].update("LazyCall"),
        },
    )

    config = minimal_conf_noscreen
    config.screens = [libqtile.config.Screen(top=libqtile.bar.Bar([textbox], 10))]

    manager_nospawn.start(config)

    topbar = manager_nospawn.c.bar["top"]
    assert topbar.widget["textbox"].info()["text"] == "Testing"

    topbar.fake_button_press(0, 0, button=1)
    assert topbar.widget["textbox"].info()["text"] == "LazyCall"
