# Widget specific tests

from libqtile.config import Screen
from libqtile.bar import Bar
from libqtile.widget import TextBox

from .utils import Xephyr
from .test_manager import BareConfig

class ColorChanger(TextBox):
    count = 0
    def update(self, text):
        self.count += 1
        if self.count % 2 == 0:
            self.foreground = "ff0000"
        else:
            self.foreground = "0000ff"
        self.text = text

class WidgetTestConf(BareConfig):
    screens = [Screen(bottom=Bar([ColorChanger(name="colorchanger")], 20))]

@Xephyr(False, WidgetTestConf())
def test_textbox_color_change(self):
    self.c.widget["colorchanger"].update('f')
    print(self.c.widget["colorchanger"].info())
    assert self.c.widget["colorchanger"].info()["foreground"] == "0000ff"

    self.c.widget["colorchanger"].update('f')
    assert self.c.widget["colorchanger"].info()["foreground"] == "ff0000"
