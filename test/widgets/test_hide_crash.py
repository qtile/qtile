# Copyright (c) 2024 Sean Vig
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
import pytest

from libqtile import bar
from libqtile.config import Screen
from libqtile.confreader import Config
from libqtile.widget.base import _Widget


class BadWidget(_Widget):
    def __init__(self, **config):
        _Widget.__init__(self, bar.CALCULATED, **config)

    def _configure(self, qtile, bar):
        _Widget._configure(self, qtile, bar)
        # Crash!
        1 / 0


class CrashConfig(Config):
    screens = [Screen(top=bar.Bar([BadWidget(), BadWidget(hide_crash=True)], 20))]


crash_config = pytest.mark.parametrize("manager", [CrashConfig], indirect=True)


@crash_config
def test_hide_crashed_widget(manager):
    widgets = manager.c.bar["top"].items("widget")[1]
    # There should only be one widget in the bar
    assert len(widgets) == 1

    # That widget should be a ConfigErrorWidget
    assert widgets[0] == "configerrorwidget"
