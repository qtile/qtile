import libqtile.bar
import libqtile.config
import libqtile.confreader
import libqtile.layout
from libqtile.widget import CurrentScreen
from test.conftest import dualmonitor

ACTIVE = "#FF0000"
INACTIVE = "#00FF00"


@dualmonitor
def test_change_screen(manager_nospawn, minimal_conf_noscreen):
    cswidget = CurrentScreen(active_color=ACTIVE, inactive_color=INACTIVE)

    config = minimal_conf_noscreen
    config.screens = [
        libqtile.config.Screen(top=libqtile.bar.Bar([cswidget], 10)),
        libqtile.config.Screen(),
    ]
    manager_nospawn.start(config)

    widget = manager_nospawn.c.widget["currentscreen"]

    assert widget.eval("self.text") == "A"
    assert widget.eval("self.layout.colour") == ACTIVE

    manager_nospawn.c.to_screen(1)

    assert widget.eval("self.text") == "I"
    assert widget.eval("self.layout.colour") == INACTIVE
