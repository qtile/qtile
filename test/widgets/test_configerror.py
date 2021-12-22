# Copyright (c) 2021 elParaguayo
#
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
import pytest

import libqtile.bar
import libqtile.config
from libqtile.widget.base import _Widget


# This widget needs to crash during _configure
class BadWidget(_Widget):
    def _configure(self, qtile, bar):
        _Widget._configure(qtile, bar)
        1 / 0

    def draw(self):
        pass


@pytest.mark.parametrize("position", ["top", "bottom", "left", "right"])
def test_configerrorwidget(manager_nospawn, minimal_conf_noscreen, position):
    """ConfigError widget should show in any bar orientation."""
    widget = BadWidget(length=10)

    config = minimal_conf_noscreen
    config.screens = [libqtile.config.Screen(**{position: libqtile.bar.Bar([widget], 10)})]

    manager_nospawn.start(config)

    testbar = manager_nospawn.c.bar[position]
    w = testbar.info()["widgets"][0]

    # Check that BadWidget has been replaced by ConfigErrorWidget
    assert w["name"] == "configerrorwidget"
    assert w["text"] == "Widget crashed: BadWidget (click to hide)"

    # Clicking on widget hides it so let's check it works
    testbar.fake_button_press(0, position, 0, 0, button=1)
    w = testbar.info()["widgets"][0]
    assert w["text"] == ""
