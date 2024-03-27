# Copyright (c) 2024 elParaguayo
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

from libqtile.config import Bar, Screen
from libqtile.confreader import Config
from libqtile.widget import do_not_disturb as dnd


class DunstStatus:
    PAUSED = False

    @classmethod
    def toggle(cls):
        cls.PAUSED = not cls.PAUSED

    @classmethod
    def toggle_and_status(cls):
        cls.toggle()
        return cls.PAUSED


def mock_check_output(args):
    status = str(DunstStatus.PAUSED).lower()
    return status.encode()


@pytest.fixture(scope="function")
def patched_dnd(monkeypatch):
    monkeypatch.setattr("libqtile.widget.do_not_disturb.check_output", mock_check_output)

    class PatchedDND(dnd.DoNotDisturb):
        def __init__(self, **config):
            dnd.DoNotDisturb.__init__(self, **config)
            DunstStatus.PAUSED = False
            self.mouse_callbacks = {"Button1": lambda: DunstStatus.toggle()}
            self.name = "donotdisturb"

    yield PatchedDND


@pytest.fixture(scope="function")
def dnd_manager(manager_nospawn, request, patched_dnd):
    class GroupConfig(Config):
        screens = [
            Screen(
                top=Bar(
                    [patched_dnd(update_interval=10, **getattr(request, "param", dict()))], 30
                )
            )
        ]

    manager_nospawn.start(GroupConfig)

    yield manager_nospawn


def config(**kwargs):
    return pytest.mark.parametrize("dnd_manager", [kwargs], indirect=True)


def test_dnd(dnd_manager):
    widget = dnd_manager.c.widget["donotdisturb"]
    assert widget.info()["text"] == "O"

    dnd_manager.c.bar["top"].fake_button_press(0, "top", 0, 0, 1)
    widget.eval("self.update(self.poll())")
    assert widget.info()["text"] == "X"

    dnd_manager.c.bar["top"].fake_button_press(0, "top", 0, 0, 1)
    widget.eval("self.update(self.poll())")
    assert widget.info()["text"] == "O"

    dnd_manager.c.bar["top"].fake_button_press(0, "top", 0, 0, 1)
    widget.eval("self.update(self.poll())")
    assert widget.info()["text"] == "X"


@config(poll_function=DunstStatus.toggle_and_status)
def test_dnd_custom_func(dnd_manager):
    widget = dnd_manager.c.widget["donotdisturb"]

    # Status is reversed here as the custom func toggles the status
    # every time it's polled
    assert widget.info()["text"] == "X"

    widget.eval("self.update(self.poll())")
    assert widget.info()["text"] == "O"

    widget.eval("self.update(self.poll())")
    assert widget.info()["text"] == "X"

    widget.eval("self.update(self.poll())")
    assert widget.info()["text"] == "O"


@config(enabled_icon="-", disabled_icon="+")
def test_dnd_custom_icons(dnd_manager):
    widget = dnd_manager.c.widget["donotdisturb"]
    assert widget.info()["text"] == "+"

    dnd_manager.c.bar["top"].fake_button_press(0, "top", 0, 0, 1)
    widget.eval("self.update(self.poll())")
    assert widget.info()["text"] == "-"
