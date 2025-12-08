import pytest

from libqtile.bar import Bar
from libqtile.command.base import expose_command
from libqtile.config import Screen
from libqtile.widget import TextBox
from test.conftest import BareConfig


class ColorChanger(TextBox):
    count = 0

    @expose_command()
    def update(self, text):
        self.count += 1
        if self.count % 2 == 0:
            self.foreground = "ff0000"
        else:
            self.foreground = "0000ff"
        self.text = text


class WidgetTestConf(BareConfig):
    screens = [Screen(bottom=Bar([ColorChanger(name="colorchanger")], 20))]


widget_conf = pytest.mark.parametrize("manager", [WidgetTestConf], indirect=True)


@widget_conf
def test_textbox_color_change(manager):
    widget = manager.c.widget["colorchanger"]

    widget.update("f")
    assert widget.eval("self.foreground") == "0000ff"

    widget.update("f")
    assert widget.eval("self.foreground") == "ff0000"
