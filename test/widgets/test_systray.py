# Copyright (c) 2022 elParaguayo
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
import libqtile.bar
import libqtile.config
from libqtile import widget


def test_no_duplicates_multiple_instances(manager_nospawn, minimal_conf_noscreen):
    """Check only one instance of Systray widget."""
    assert not widget.Systray._instances
    config = minimal_conf_noscreen
    config.screens = [
        libqtile.config.Screen(top=libqtile.bar.Bar([widget.Systray(), widget.Systray()], 10))
    ]

    manager_nospawn.start(config)

    widgets = manager_nospawn.c.bar["top"].info()["widgets"]
    assert len(widgets) == 2
    assert widgets[1]["name"] == "configerrorwidget"


def test_no_duplicates_mirror(manager_nospawn, minimal_conf_noscreen):
    """Check systray is not mirrored."""
    assert not widget.Systray._instances
    systray = widget.Systray()
    config = minimal_conf_noscreen
    config.fake_screens = [
        libqtile.config.Screen(
            top=libqtile.bar.Bar([systray], 10),
            x=0,
            y=0,
            width=300,
            height=300,
        ),
        libqtile.config.Screen(
            top=libqtile.bar.Bar([systray], 10),
            x=0,
            y=300,
            width=300,
            height=300,
        ),
    ]

    manager_nospawn.start(config)

    # Second screen has tried to mirror the Systray instance
    widgets = manager_nospawn.c.screen[1].bar["top"].info()["widgets"]
    assert len(widgets) == 1
    assert widgets[0]["name"] == "configerrorwidget"
