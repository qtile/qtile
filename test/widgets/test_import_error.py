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
from libqtile import widget


def bad_importer(*args, **kwargs):
    raise ImportError()


@pytest.mark.parametrize("position", ["top", "bottom", "left", "right"])
def test_importerrorwidget(monkeypatch, manager_nospawn, minimal_conf_noscreen, position):
    """Check we get an ImportError widget with missing import?"""
    monkeypatch.setattr("libqtile.utils.importlib.import_module", bad_importer)

    badwidget = widget.TextBox("I am a naughty widget.")

    config = minimal_conf_noscreen
    config.screens = [libqtile.config.Screen(**{position: libqtile.bar.Bar([badwidget], 10)})]

    manager_nospawn.start(config)

    testbar = manager_nospawn.c.bar[position]
    w = testbar.info()["widgets"][0]

    # Check that the widget has been replaced with an ImportError
    assert w["name"] == "importerrorwidget"
    assert w["text"] == "Import Error: TextBox"
