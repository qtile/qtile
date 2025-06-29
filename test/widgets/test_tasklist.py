# Copyright (c) 2023 elParaguayo
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

import libqtile.config
from libqtile import bar, layout
from libqtile.config import Screen
from libqtile.confreader import Config
from libqtile.widget.tasklist import TaskList
from test.layouts.layout_utils import assert_focused
from test.test_scratchpad import is_spawned, spawn_cmd


class TaskListTestWidget(TaskList):
    def __init__(self, *args, **kwargs):
        TaskList.__init__(self, *args, **kwargs)
        self._text = ""

    def calc_box_widths(self):
        ret_val = TaskList.calc_box_widths(self)
        self._text = "|".join(self.get_taskname(w) for w in self.windows)
        return ret_val

    def info(self):
        info = TaskList.info(self)
        info["text"] = self._text
        return info


@pytest.fixture
def override_xdg(request):
    return getattr(request, "param", False)


@pytest.fixture
def position(request):
    return getattr(request, "param", "top")


xdg = pytest.mark.parametrize("override_xdg", [True], indirect=True)
no_xdg = pytest.mark.parametrize("override_xdg", [False], indirect=True)
horizontal_and_vertical = pytest.mark.parametrize("position", ["top", "left"], indirect=True)


@pytest.fixture
def tasklist_manager(request, manager_nospawn, override_xdg, monkeypatch, position):
    monkeypatch.setattr("libqtile.widget.tasklist.has_xdg", override_xdg)

    config = getattr(request, "param", dict())

    class TasklistConfig(Config):
        auto_fullscreen = True
        groups = [
            libqtile.config.ScratchPad(
                "SCRATCHPAD",
                dropdowns=[
                    libqtile.config.DropDown("dd-a", spawn_cmd("dd-a"), on_focus_lost_hide=False),
                ],
            ),
            libqtile.config.Group("a"),
            libqtile.config.Group("b"),
        ]
        layouts = [layout.Stack()]
        floating_layout = libqtile.resources.default_config.floating_layout
        keys = []
        mouse = []
        screens = [
            Screen(**{position: bar.Bar([TaskListTestWidget(name="tasklist", **config)], 28)})
        ]

    manager_nospawn.start(TasklistConfig)
    yield manager_nospawn


def configure_tasklist(**config):
    """Decorator to pass configuration to widget."""
    return pytest.mark.parametrize("tasklist_manager", [config], indirect=True)


@horizontal_and_vertical
def test_tasklist_defaults(tasklist_manager):
    widget = tasklist_manager.c.widget["tasklist"]

    tasklist_manager.test_window("One")
    tasklist_manager.test_window("Two")
    assert widget.info()["text"] == "One|Two"

    # Test floating
    tasklist_manager.c.window.toggle_floating()
    assert widget.info()["text"] == "One|V Two"

    tasklist_manager.c.window.toggle_floating()
    assert widget.info()["text"] == "One|Two"

    # Test maximize
    tasklist_manager.c.window.toggle_maximize()
    assert widget.info()["text"] == "One|[] Two"

    tasklist_manager.c.window.toggle_maximize()
    assert widget.info()["text"] == "One|Two"

    # Test minimize
    tasklist_manager.c.window.toggle_minimize()
    assert widget.info()["text"] == "One|_ Two"

    tasklist_manager.c.window.toggle_minimize()
    assert widget.info()["text"] == "One|Two"


def test_tasklist_skip_taskbar_defaults(tasklist_manager):
    widget = tasklist_manager.c.widget["tasklist"]
    tasklist_manager.c.group["SCRATCHPAD"].dropdown_reconfigure("dd-a")

    tasklist_manager.test_window("one")
    assert_focused(tasklist_manager, "one")

    # dd-a has no window associated yet
    assert "window" not in tasklist_manager.c.group["SCRATCHPAD"].dropdown_info("dd-a")

    # First toggling: wait for window
    tasklist_manager.c.group["SCRATCHPAD"].dropdown_toggle("dd-a")
    is_spawned(tasklist_manager, "dd-a")
    assert_focused(tasklist_manager, "dd-a")
    assert (
        tasklist_manager.c.group["SCRATCHPAD"].dropdown_info("dd-a")["window"]["name"] == "dd-a"
    )

    if tasklist_manager.c.core.info()["backend"] == "x11":
        # check that window's _NET_WM_STATE contains _NET_WM_STATE_SKIP_TASKBAR
        net_wm_state = tasklist_manager.c.window.eval(
            'self.window.get_property("_NET_WM_STATE", "ATOM", unpack=int)'
        )[1]
        skip_taskbar = tasklist_manager.c.window.eval(
            'self.qtile.core.conn.atoms["_NET_WM_STATE_SKIP_TASKBAR"]'
        )[1]
        assert skip_taskbar in net_wm_state
        assert tasklist_manager.c.window.eval("self.window.get_wm_type()")[1] == "normal"
        assert widget.info()["text"] == "one"


@configure_tasklist(txt_minimized="(min) ", txt_maximized="(max) ", txt_floating="(float) ")
def test_tasklist_custom_text(tasklist_manager):
    widget = tasklist_manager.c.widget["tasklist"]

    tasklist_manager.test_window("One")
    tasklist_manager.test_window("Two")
    assert widget.info()["text"] == "One|Two"

    # Test floating
    tasklist_manager.c.window.toggle_floating()
    assert widget.info()["text"] == "One|(float) Two"

    tasklist_manager.c.window.toggle_floating()
    assert widget.info()["text"] == "One|Two"

    # Test maximize
    tasklist_manager.c.window.toggle_maximize()
    assert widget.info()["text"] == "One|(max) Two"

    tasklist_manager.c.window.toggle_maximize()
    assert widget.info()["text"] == "One|Two"

    # Test minimize
    tasklist_manager.c.window.toggle_minimize()
    assert widget.info()["text"] == "One|(min) Two"

    tasklist_manager.c.window.toggle_minimize()
    assert widget.info()["text"] == "One|Two"


@configure_tasklist(markup_minimized="_{}_", markup_maximized="[{}]", markup_floating="V{}V")
def test_tasklist_custom_markup(tasklist_manager):
    """markup_* options override txt_*"""
    widget = tasklist_manager.c.widget["tasklist"]

    tasklist_manager.test_window("One")
    tasklist_manager.test_window("Two")
    assert widget.info()["text"] == "One|Two"

    # Test floating
    tasklist_manager.c.window.toggle_floating()
    assert widget.info()["text"] == "One|VTwoV"

    tasklist_manager.c.window.toggle_floating()
    assert widget.info()["text"] == "One|Two"

    # Test maximize
    tasklist_manager.c.window.toggle_maximize()
    assert widget.info()["text"] == "One|[Two]"

    tasklist_manager.c.window.toggle_maximize()
    assert widget.info()["text"] == "One|Two"

    # Test minimize
    tasklist_manager.c.window.toggle_minimize()
    assert widget.info()["text"] == "One|_Two_"

    tasklist_manager.c.window.toggle_minimize()
    assert widget.info()["text"] == "One|Two"


@configure_tasklist(markup_focused="({})", markup_focused_floating="[{}]")
def test_tasklist_focused_and_floating(tasklist_manager):
    widget = tasklist_manager.c.widget["tasklist"]

    tasklist_manager.test_window("One")
    tasklist_manager.test_window("Two")
    assert widget.info()["text"] == "One|(Two)"

    # Test floating
    tasklist_manager.c.window.toggle_floating()
    assert widget.info()["text"] == "One|[Two]"

    tasklist_manager.c.window.toggle_floating()
    assert widget.info()["text"] == "One|(Two)"


@pytest.mark.parametrize(
    "position,coords",
    [("top", (0, 0, 1)), ("right", (0, 0, 1)), ("left", (0, 599, 1))],
    indirect=["position"],
)
@configure_tasklist(margin=0)
def test_tasklist_click_task(tasklist_manager, position, coords):
    tasklist_manager.test_window("One")
    tasklist_manager.test_window("Two")

    # Current focused window is "Two"
    assert tasklist_manager.c.window.info()["name"] == "Two"

    # Click in top left corner of bar means we click on "One"
    # which should focus the window
    # margin is set to 0 as value set by widget_defaults means text would otherwise
    # mean text does not start at x=0
    tasklist_manager.c.bar[position].fake_button_press(*coords)
    assert tasklist_manager.c.window.info()["name"] == "One"


@xdg
@configure_tasklist(theme_mode="non-existent-mode")
@pytest.mark.xfail
def test_tasklist_bad_theme_mode(tasklist_manager):
    msgs = tasklist_manager.get_log_buffer()
    assert "Unexpected theme_mode (non-existent-mode). Theme icons will be disabled." in msgs


@no_xdg
@configure_tasklist(theme_mode="non-existent-mode")
@pytest.mark.xfail
def test_tasklist_no_xdg(tasklist_manager):
    msgs = tasklist_manager.get_log_buffer()
    assert "You must install pyxdg to use theme icons." in msgs


@horizontal_and_vertical
@configure_tasklist(stretch=False)
def test_tasklist_no_stretch(tasklist_manager, position):
    widget = tasklist_manager.c.widget["tasklist"]
    tasklist_manager.test_window("One")
    width_one = widget.info()["length"]

    tasklist_manager.test_window("Two")
    width_two = widget.info()["length"]

    assert width_one != width_two
