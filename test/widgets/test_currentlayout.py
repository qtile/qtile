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
from libqtile import widget


def get_widget_config(_widget, config):
    config.screens = [
        libqtile.config.Screen(top=libqtile.bar.Bar([_widget], 10)),
    ]
    config.layouts = [
        libqtile.layout.Columns(),
        libqtile.layout.Max(),
        libqtile.layout.Stack(),
    ]
    return config


def test_current_layout(manager_nospawn, minimal_conf_noscreen):
    config = get_widget_config(widget.CurrentLayout(), minimal_conf_noscreen)
    manager_nospawn.start(config)
    topbar = manager_nospawn.c.bar["top"]

    layout = topbar.info()["widgets"][0]["text"]
    assert layout == "columns"

    manager_nospawn.c.next_layout()
    layout = topbar.info()["widgets"][0]["text"]
    assert layout == "max"

    manager_nospawn.c.prev_layout()
    layout = topbar.info()["widgets"][0]["text"]
    assert layout == "columns"

    topbar.fake_button_press(0, 0, button=1)
    layout = topbar.info()["widgets"][0]["text"]
    assert layout == "max"

    topbar.fake_button_press(0, 0, button=2)
    layout = topbar.info()["widgets"][0]["text"]
    assert layout == "columns"

    manager_nospawn.c.screen.next_group()
    manager_nospawn.c.to_layout_index(-1)
    layout = topbar.info()["widgets"][0]["text"]
    assert layout == "stack"

    manager_nospawn.c.screen.prev_group()
    layout = topbar.info()["widgets"][0]["text"]
    assert layout == "columns"


def test_current_layout_icon(manager_nospawn, minimal_conf_noscreen):
    config = get_widget_config(widget.CurrentLayoutIcon(), minimal_conf_noscreen)
    manager_nospawn.start(config)
    topbar = manager_nospawn.c.bar["top"]

    icons = int(topbar.eval("len(self.widgets[0].surfaces)")[1])
    assert icons == 3

    length = int(topbar.eval("self.widgets[0].length")[1])
    assert length != 0


def test_current_layout_draw_icon_first(manager_nospawn, minimal_conf_noscreen):
    config = get_widget_config(
        widget.CurrentLayoutIconOrText(draw_icon_first=True), minimal_conf_noscreen
    )
    manager_nospawn.start(config)
    topbar = manager_nospawn.c.bar["top"]
    image_length = int(topbar.eval("self.widgets[0].image_length")[1])

    length = int(topbar.eval("self.widgets[0].length")[1])
    assert length == image_length

    topbar.fake_button_press(0, 0, button=3)
    length = int(topbar.eval("self.widgets[0].length")[1])
    assert length != image_length

    topbar.fake_button_press(0, 0, button=3)
    length = int(topbar.eval("self.widgets[0].length")[1])
    assert length == image_length


def test_current_layout_draw_text_first(manager_nospawn, minimal_conf_noscreen):
    config = get_widget_config(
        widget.CurrentLayoutIconOrText(draw_icon_first=False), minimal_conf_noscreen
    )
    manager_nospawn.start(config)
    topbar = manager_nospawn.c.bar["top"]
    image_length = int(topbar.eval("self.widgets[0].image_length")[1])

    length = int(topbar.eval("self.widgets[0].length")[1])
    assert length != image_length
