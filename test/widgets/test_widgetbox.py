import libqtile.bar
import libqtile.config
import libqtile.confreader
import libqtile.layout
from libqtile.widget import TextBox, WidgetBox


def no_op(*args, **kwargs):
    pass


class MinimalConf(libqtile.confreader.Config):
    auto_fullscreen = False
    keys = []
    mouse = []
    groups = [libqtile.config.Group("a")]
    layouts = [libqtile.layout.stack.Stack(num_stacks=1)]
    floating_layout = libqtile.resources.default_config.floating_layout
    screens = []


def test_widgetbox_widget(manager_nospawn):

    # Create some widgets to put in the widgetbox
    tb_one = TextBox(name="tb_one", text="TB ONE")
    tb_two = TextBox(name="tb_two", text="TB TWO")

    # Give widgetbox invalid value for button location
    widget_box = WidgetBox(widgets=[tb_one, tb_two],
                           close_button_location="middle",
                           fontsize=10)

    config = MinimalConf()
    config.screens = [libqtile.config.Screen(top=libqtile.bar.Bar([widget_box], 10))]

    manager_nospawn.start(config)

    i = manager_nospawn.c.bar["top"].info
    w = manager_nospawn.c.widget["widgetbox"]

    # Invalid value should be corrected to default
    assert w.info()["location"] == "left"

    # Check only widget in bar is widgetbox
    assert len(i()["widgets"]) == 1

    # Open box
    w.toggle()

    # Check it's open
    assert w.info()["open"]

    # Default text position is left
    widgets = i()["widgets"]
    boxed = [w["name"] for w in widgets]
    assert boxed == ["widgetbox", "tb_one", "tb_two"]

    # Close box
    w.toggle()

    # Check it's closed
    assert not w.info()["open"]

    # Check widgets have been removed
    widgets = i()["widgets"]
    boxed = [w["name"] for w in widgets]
    assert boxed == ["widgetbox"]

    # Move button to right-hand side
    w.set_location("right")

    # Re-open box with new layout
    w.toggle()

    # Now widgetbox is on the right
    widgets = i()["widgets"]
    boxed = [w["name"] for w in widgets]
    assert boxed == ["tb_one", "tb_two", "widgetbox"]
