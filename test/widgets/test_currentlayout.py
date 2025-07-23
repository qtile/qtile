# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

# Widget specific tests

import libqtile.bar
import libqtile.config
import libqtile.confreader
import libqtile.layout
from libqtile.widget import CurrentLayout


def get_widget_config(widget, config):
    config.screens = [
        libqtile.config.Screen(top=libqtile.bar.Bar([widget], 10)),
    ]
    config.layouts = [
        libqtile.layout.Columns(),
        libqtile.layout.Max(),
        libqtile.layout.Stack(),
    ]
    return config


def test_current_layout(manager_nospawn, minimal_conf_noscreen):
    config = get_widget_config(CurrentLayout(), minimal_conf_noscreen)
    manager_nospawn.start(config)
    widget = manager_nospawn.c.widget["currentlayout"]

    layout = widget.info()["text"]
    assert layout == "columns"

    manager_nospawn.c.next_layout()
    layout = widget.info()["text"]
    assert layout == "max"

    manager_nospawn.c.prev_layout()
    layout = widget.info()["text"]
    assert layout == "columns"

    widget.bar.fake_button_press(0, 0, button=1)
    layout = widget.info()["text"]
    assert layout == "max"

    widget.bar.fake_button_press(0, 0, button=2)
    layout = widget.info()["text"]
    assert layout == "columns"

    manager_nospawn.c.screen.next_group()
    manager_nospawn.c.to_layout_index(-1)
    layout = widget.info()["text"]
    assert layout == "stack"

    manager_nospawn.c.screen.prev_group()
    layout = widget.info()["text"]
    assert layout == "columns"


def test_current_layout_icon_mode(manager_nospawn, minimal_conf_noscreen):
    config = get_widget_config(CurrentLayout(mode="icon"), minimal_conf_noscreen)
    manager_nospawn.start(config)
    widget = manager_nospawn.c.widget["currentlayout"]
    img_length = int(widget.eval("self.img_length")[1])
    padding = int(widget.eval("self.padding")[1])
    text_length = int(widget.eval("super(type(self), self).calculate_length()")[1])

    length = int(widget.eval("self.length")[1])
    assert length == img_length + padding * 2

    widget.bar.fake_button_press(0, 0, button=3)
    length = int(widget.eval("self.length")[1])
    assert length == text_length

    widget.bar.fake_button_press(0, 0, button=3)
    length = int(widget.eval("self.length")[1])
    assert length == img_length + padding * 2


def test_current_layout_text_mode(manager_nospawn, minimal_conf_noscreen):
    config = get_widget_config(CurrentLayout(mode="text"), minimal_conf_noscreen)
    manager_nospawn.start(config)
    widget = manager_nospawn.c.widget["currentlayout"]
    img_length = int(widget.eval("self.img_length")[1])
    padding = int(widget.eval("self.padding")[1])
    text_length = int(widget.eval("super(type(self), self).calculate_length()")[1])

    length = int(widget.eval("self.length")[1])
    assert length == text_length

    widget.bar.fake_button_press(0, 0, button=3)
    length = int(widget.eval("self.length")[1])
    assert length == img_length + padding * 2

    widget.bar.fake_button_press(0, 0, button=3)
    length = int(widget.eval("self.length")[1])
    assert length == text_length


def test_current_layout_both_mode(manager_nospawn, minimal_conf_noscreen):
    config = get_widget_config(CurrentLayout(mode="both"), minimal_conf_noscreen)
    manager_nospawn.start(config)
    widget = manager_nospawn.c.widget["currentlayout"]
    img_length = int(widget.eval("self.img_length")[1])
    padding = int(widget.eval("self.padding")[1])
    text_length = int(widget.eval("super(type(self), self).calculate_length()")[1])

    length = int(widget.eval("self.length")[1])
    assert length == text_length + img_length + padding

    widget.bar.fake_button_press(0, 0, button=3)
    length = int(widget.eval("self.length")[1])
    assert length == text_length + img_length + padding
