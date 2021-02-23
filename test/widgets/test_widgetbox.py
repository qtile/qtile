from libqtile.bar import Bar
from libqtile.widget import TextBox, WidgetBox


def no_op(*args, **kwargs):
    pass


class FakeWindow:
    class _NestedWindow:
        wid = 10

    window = _NestedWindow()


def test_widgetbox_widget(fake_qtile):

    tb_one = TextBox(name="tb_one", text="TB ONE")
    tb_two = TextBox(name="tb_two", text="TB TWO")

    # Give widgetbox invalid value for button location
    widget_box = WidgetBox([tb_one, tb_two],
                           close_button_location="middle",
                           fontsize=10)

    # Create a bar and set attributes needed to run widget
    fakebar = Bar([widget_box], 24)
    fakebar.window = FakeWindow()
    fakebar.width = 10
    fakebar.height = 10
    fakebar.draw = no_op

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
