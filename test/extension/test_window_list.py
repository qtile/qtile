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
import pytest

import libqtile.bar
import libqtile.config
import libqtile.layout
from libqtile.confreader import Config
from libqtile.extension.window_list import WindowList
from libqtile.lazy import lazy


@pytest.fixture
def extension_manager(monkeypatch, manager_nospawn):
    extension = WindowList()

    # We want the value returned immediately
    def fake_popen(cmd, *args, **kwargs):
        class PopenObj:
            def communicate(self, value_in, *args):
                return [value_in, None]

        return PopenObj()

    monkeypatch.setattr("libqtile.extension.base.Popen", fake_popen)

    class ManagerConfig(Config):
        groups = [
            libqtile.config.Group("a"),
            libqtile.config.Group("b"),
        ]
        layouts = [libqtile.layout.max.Max()]
        keys = [
            libqtile.config.Key(["control"], "k", lazy.run_extension(extension)),
        ]
        screens = [
            libqtile.config.Screen(
                bottom=libqtile.bar.Bar([], 20),
            )
        ]

    manager_nospawn.start(ManagerConfig)

    yield manager_nospawn


def test_window_list(extension_manager):
    """Test WindowList extension switches group."""

    # Launch a window and verify it's on the current group
    extension_manager.test_window("one")
    assert len(extension_manager.c.group.info()["windows"]) == 1

    # Switch group and verify no windows in group
    extension_manager.c.group["b"].toscreen()
    assert len(extension_manager.c.group.info()["windows"]) == 0

    # Toggle extension (which is patched to return immediately)
    # Check that window is visible on original group
    extension_manager.c.simulate_keypress(["control"], "k")
    assert len(extension_manager.c.group.info()["windows"]) == 1
    assert extension_manager.c.group.info()["label"] == "a"
