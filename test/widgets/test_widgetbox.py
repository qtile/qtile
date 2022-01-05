import libqtile.config
from libqtile.widget import TextBox, WidgetBox
from test.widgets.conftest import FakeBar


def test_widgetbox_widget(fake_qtile, fake_window):

    tb_one = TextBox(name="tb_one", text="TB ONE")
    tb_two = TextBox(name="tb_two", text="TB TWO")

    # Give widgetbox invalid value for button location
    widget_box = WidgetBox([tb_one, tb_two], close_button_location="middle", fontsize=10)

    # Create a bar and set attributes needed to run widget
    fakebar = FakeBar([widget_box], window=fake_window)

    # Configure the widget box
    widget_box._configure(fake_qtile, fakebar)

    # Invalid value should be corrected to default
    assert widget_box.close_button_location == "left"

    # Check only widget in bar is widgetbox
    assert fakebar.widgets == [widget_box]

    # Open box
    widget_box.cmd_toggle()

    # Check it's open
    assert widget_box.box_is_open

    # Default text position is left
    assert fakebar.widgets == [widget_box, tb_one, tb_two]

    # Close box
    widget_box.cmd_toggle()

    # Check it's closed
    assert not widget_box.box_is_open

    # Check widgets have been removed
    assert fakebar.widgets == [widget_box]

    # Move button to right-hand side
    widget_box.close_button_location = "right"

    # Re-open box with new layout
    widget_box.cmd_toggle()

    # Now widgetbox is on the right
    assert fakebar.widgets == [tb_one, tb_two, widget_box]


def test_widgetbox_mirror(manager_nospawn, minimal_conf_noscreen):
    config = minimal_conf_noscreen
    tbox = TextBox(text="Text Box")
    config.screens = [libqtile.config.Screen(top=libqtile.bar.Bar([tbox, WidgetBox([tbox])], 10))]

    manager_nospawn.start(config)

    manager_nospawn.c.widget["widgetbox"].toggle()
    topbar = manager_nospawn.c.bar["top"]
    widgets = [w["name"] for w in topbar.info()["widgets"]]
    assert widgets == ["textbox", "widgetbox", "mirror"]


def test_widgetbox_mouse_click(manager_nospawn, minimal_conf_noscreen):
    config = minimal_conf_noscreen
    tbox = TextBox(text="Text Box")
    config.screens = [libqtile.config.Screen(top=libqtile.bar.Bar([WidgetBox([tbox])], 10))]

    manager_nospawn.start(config)

    topbar = manager_nospawn.c.bar["top"]
    assert len(topbar.info()["widgets"]) == 1

    topbar.fake_button_press(0, "top", 0, 0, button=1)
    assert len(topbar.info()["widgets"]) == 2

    topbar.fake_button_press(0, "top", 0, 0, button=1)
    assert len(topbar.info()["widgets"]) == 1
