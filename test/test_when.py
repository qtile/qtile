# Copyright (c) 2021 Jeroen Wijenbergh
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

from libqtile import config, layout
from libqtile.confreader import Config
from libqtile.lazy import lazy


# Config with multiple keys and when checks
class WhenConfig(Config):
    keys = [
        config.Key(
            ["control"],
            "k",
            lazy.window.toggle_floating(),
        ),
        config.Key(
            ["control"],
            "j",
            lazy.window.toggle_floating().when(focused=config.Match(wm_class="TestWindow")),
        ),
        config.Key(
            ["control"],
            "h",
            lazy.window.toggle_floating().when(focused=config.Match(wm_class="idonotexist")),
        ),
        config.Key(
            ["control"],
            "n",
            lazy.next_layout().when(focused=config.Match(wm_class="TestWindow")),
        ),
        config.Key(
            ["control"],
            "m",
            lazy.next_layout().when(
                focused=config.Match(wm_class="TestWindow"), if_no_focused=True
            ),
        ),
    ]
    layouts = [layout.MonadWide(), layout.MonadTall()]


when_config = pytest.mark.parametrize("manager", [WhenConfig], indirect=True)


@when_config
def test_when(manager):
    # Check if the test window is alive and tiled
    one = manager.test_window("one")
    assert not manager.c.window.info()["floating"]

    # This sets the window to floating as there is no when
    manager.c.simulate_keypress(["control"], "k")
    assert manager.c.window.info()["floating"]

    # This keeps the window floating as the class doesn't match
    manager.c.simulate_keypress(["control"], "h")
    assert manager.c.window.info()["floating"]

    # This sets the window tiled as the class does match
    manager.c.simulate_keypress(["control"], "j")
    assert not manager.c.window.info()["floating"]

    # Kill the window to create an empty group
    manager.kill_window(one)
    prev_layout_info = manager.c.layout.info()

    # This does not go to the next layout as empty is not matched
    manager.c.simulate_keypress(["control"], "n")
    assert manager.c.layout.info() == prev_layout_info

    # This does go to the next layout as empty is matched
    manager.c.simulate_keypress(["control"], "m")
    assert manager.c.layout.info() != prev_layout_info
