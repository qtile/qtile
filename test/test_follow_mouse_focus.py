import ast

import pytest

from libqtile import config
from libqtile.lazy import lazy
from test.conftest import dualmonitor
from test.helpers import assert_window_died, window_by_name
from test.test_manager import ManagerConfig


class FollowMouseFocus(ManagerConfig):
    mouse = [
        config.Click(["mod4"], "Button1"),
        config.Drag(
            ["mod4"],
            "Button3",
            lazy.window.set_position_floating(),
            start=lazy.window.get_position(),
        ),
    ]
    follow_mouse_focus = True


class FollowMouseFocusFalse(FollowMouseFocus):
    follow_mouse_focus = False


class FollowMouseFocusClickOrDragOnly(FollowMouseFocus):
    follow_mouse_focus = "click_or_drag_only"


@pytest.fixture
def follow_mouse_focus(request):
    return request.param


follow_mouse_focus_config = pytest.mark.parametrize(
    "manager, follow_mouse_focus",
    [
        (FollowMouseFocus, True),
        (FollowMouseFocusFalse, False),
        (FollowMouseFocusClickOrDragOnly, "click_or_drag_only"),
    ],
    indirect=True,
)


@follow_mouse_focus_config
def test_follow_mouse_focus(manager, follow_mouse_focus):
    manager.test_window("one")
    manager.c.window.set_position_floating(50, 50)
    manager.c.window.set_size_floating(50, 50)

    manager.test_window("two")
    manager.c.window.set_position_floating(150, 50)
    manager.c.window.set_size_floating(50, 50)

    # Last focused windows
    assert_window = manager.c.window.info()["name"]

    # Go to window one
    manager.backend.fake_motion(55, 55)
    if follow_mouse_focus is True:
        assert_window = "one"
    assert manager.c.window.info()["name"] == assert_window
    # Send fake Drag event
    manager.backend.hold_modifier("super")
    manager.backend.fake_button_press(3)
    manager.backend.fake_motion(65, 65)
    manager.backend.fake_button_release(3)
    manager.backend.release_modifier("super")
    if follow_mouse_focus == "click_or_drag_only":
        assert_window = "one"
    assert manager.c.window.info()["name"] == assert_window

    # Go to window two
    manager.backend.fake_motion(155, 55)
    if follow_mouse_focus is True:
        assert_window = "two"
    assert manager.c.window.info()["name"] == assert_window
    # Send fake Click event
    manager.backend.hold_modifier("super")
    manager.backend.fake_button_press(1)
    manager.backend.fake_button_release(1)
    manager.backend.release_modifier("super")
    if follow_mouse_focus == "click_or_drag_only":
        assert_window = "two"
    assert manager.c.window.info()["name"] == assert_window


@dualmonitor
@follow_mouse_focus_config
def test_follow_mouse_focus_across_screens(manager, follow_mouse_focus):
    manager.test_window("one")
    manager.c.window.set_position_floating(50, 50)
    manager.c.window.set_size_floating(50, 50)

    manager.c.to_screen(1)
    manager.test_window("two")
    manager.c.window.set_position_floating(850, 50)
    manager.c.window.set_size_floating(50, 50)

    assert manager.c.screen[0].group.info()["windows"] == ["one"]
    assert manager.c.screen[1].group.info()["windows"] == ["two"]

    # Last focused windows
    assert_window = manager.c.window.info()["name"]

    # Go to window one
    manager.backend.warp_pointer(55, 55)
    if follow_mouse_focus is True:
        assert_window = "one"
    assert manager.c.window.info()["name"] == assert_window
    # Send fake Drag event
    manager.backend.hold_modifier("super")
    manager.backend.fake_button_press(3)
    manager.backend.fake_button_release(3)
    manager.backend.release_modifier("super")
    if follow_mouse_focus == "click_or_drag_only":
        assert_window = "one"
    assert manager.c.window.info()["name"] == assert_window

    # Go to window two
    manager.backend.warp_pointer(855, 55)
    if follow_mouse_focus is True:
        assert_window = "two"
    assert manager.c.window.info()["name"] == assert_window
    # Send fake Click event
    manager.backend.hold_modifier("super")
    manager.backend.fake_button_press(1)
    manager.backend.fake_button_release(1)
    manager.backend.release_modifier("super")
    if follow_mouse_focus == "click_or_drag_only":
        assert_window = "two"
    assert manager.c.window.info()["name"] == assert_window


@dualmonitor
@follow_mouse_focus_config
def test_follow_mouse_focus_on_static(manager, follow_mouse_focus):
    manager.test_window("one")
    manager.c.window.static(0, 50, 50, 50, 50)

    manager.test_window("two")
    manager.c.window.static(1, 50, 50, 50, 50)

    assert manager.c.screen[0].group.info()["windows"] == []
    assert manager.c.screen[1].group.info()["windows"] == []

    # Last focused screen
    assert_screen = manager.c.screen.info()["index"]

    # Go to window two
    manager.backend.warp_pointer(855, 55)
    if follow_mouse_focus is True:
        assert_screen = 1
    assert manager.c.screen.info()["index"] == assert_screen
    # Send fake Drag event
    manager.backend.hold_modifier("super")
    manager.backend.fake_button_press(3)
    manager.backend.fake_button_release(3)
    manager.backend.release_modifier("super")
    if follow_mouse_focus == "click_or_drag_only":
        assert_screen = 1
    assert manager.c.screen.info()["index"] == assert_screen

    # Go to window one
    manager.backend.warp_pointer(55, 55)
    if follow_mouse_focus is True:
        assert_screen = 0
    assert manager.c.screen.info()["index"] == assert_screen
    manager.backend.hold_modifier("super")
    manager.backend.fake_button_press(1)
    manager.backend.fake_button_release(1)
    manager.backend.release_modifier("super")
    if follow_mouse_focus == "click_or_drag_only":
        assert_screen = 0
    assert manager.c.screen.info()["index"] == assert_screen


@follow_mouse_focus_config
def test_follow_mouse_focus_to_window_below_after_close(manager, follow_mouse_focus):
    """
    Closing the window under the pointer with follow_mouse_focus=True must
    focus the window that becomes visible underneath, not the layout's
    fallback focus (here: "elsewhere").
    """
    # Three floating windows. "elsewhere" is the layout's next-focus after
    # "above", but it is not under the pointer.
    manager.test_window("below")
    manager.c.window.set_position_floating(50, 50)
    manager.c.window.set_size_floating(100, 100)

    manager.test_window("above")
    manager.c.window.set_position_floating(50, 50)
    manager.c.window.set_size_floating(100, 100)

    manager.test_window("elsewhere")
    manager.c.window.set_position_floating(150, 50)
    manager.c.window.set_size_floating(100, 100)

    # Move over and focus "above" window
    manager.backend.fake_click(55, 55)
    assert manager.c.window.info()["name"] == "above"

    # Kill "above" window
    above_info = manager.c.window.info()
    manager.c.window.kill()
    assert_window_died(manager.c, above_info)

    if follow_mouse_focus is True:
        # The window now under the pointer must take focus
        assert manager.c.window.info()["name"] == "below"
    else:
        # Fallback window takes focus
        assert manager.c.window.info()["name"] == "elsewhere"

    # Send fake Drag event
    manager.backend.hold_modifier("super")
    manager.backend.fake_button_press(3)
    manager.backend.fake_motion(65, 65)
    manager.backend.fake_button_release(3)
    manager.backend.release_modifier("super")

    info = manager.c.window.info()
    if follow_mouse_focus is False:
        # "elsewhere" window should maintain focus and move
        assert manager.c.window.info()["name"] == "elsewhere"
        assert (info["x"], info["y"]) == (160, 60)  # 150 + 10, 50 + 10
    else:
        # "below" window should maintain or take focus and move
        assert manager.c.window.info()["name"] == "below"
        assert (info["x"], info["y"]) == (60, 60)  # 50 + 10, 50 + 10

    # Kill remaining windows
    for _ in range(2):
        win_info = manager.c.window.info()
        manager.c.window.kill()
        assert_window_died(manager.c, win_info)

    # Hovered window should be cleared
    assert manager.c.eval("self.hovered_window is None") == "True"


# Is window name_a above window name_b
def is_stacked_above(manager, name_a, name_b):
    if manager.backend.name == "wayland":
        order = manager.c.core.query_tree()
    else:
        order = ast.literal_eval(manager.c.core.eval("list(self._root.query_tree())"))
    id_a = window_by_name(manager.c, name_a).info()["id"]
    id_b = window_by_name(manager.c, name_b).info()["id"]
    return order.index(id_a) > order.index(id_b)


@follow_mouse_focus_config
def test_follow_mouse_focus_z_layer(manager, follow_mouse_focus):
    """
    Bringing a window under the pointer, by raising or lowering windows in z,
    should not focus that window when follow_mouse_focus = True. Click or Drag
    should focus it
    """

    manager.test_window("below")
    manager.c.window.set_position_floating(50, 50)
    manager.c.window.set_size_floating(100, 100)

    manager.test_window("above")
    manager.c.window.set_position_floating(50, 50)
    manager.c.window.set_size_floating(100, 100)

    manager.backend.fake_click(55, 55)
    assert manager.c.window.info()["name"] == "above"
    window_by_name(manager.c, "above").move_to_bottom()
    assert is_stacked_above(manager, "below", "above")
    assert manager.c.window.info()["name"] == "above"

    if follow_mouse_focus is False:
        manager.c.group.focus_by_name("below")
    else:
        manager.backend.hold_modifier("super")
        manager.backend.fake_button_press(1)
        manager.backend.fake_button_release(1)
        manager.backend.release_modifier("super")
    assert manager.c.window.info()["name"] == "below"
    window_by_name(manager.c, "below").move_down()
    assert is_stacked_above(manager, "above", "below")
    assert manager.c.window.info()["name"] == "below"

    if follow_mouse_focus is False:
        manager.c.group.focus_by_name("above")
    else:
        manager.backend.hold_modifier("super")
        manager.backend.fake_button_press(1)
        manager.backend.fake_button_release(1)
        manager.backend.release_modifier("super")
    assert manager.c.window.info()["name"] == "above"
    window_by_name(manager.c, "below").move_to_top()
    assert is_stacked_above(manager, "below", "above")
    assert manager.c.window.info()["name"] == "above"

    if follow_mouse_focus is False:
        manager.c.group.focus_by_name("below")
    else:
        manager.backend.hold_modifier("super")
        manager.backend.fake_button_press(1)
        manager.backend.fake_button_release(1)
        manager.backend.release_modifier("super")
    assert manager.c.window.info()["name"] == "below"
    window_by_name(manager.c, "above").move_up()
    assert is_stacked_above(manager, "above", "below")
    assert manager.c.window.info()["name"] == "below"

    if follow_mouse_focus is False:
        manager.c.group.focus_by_name("above")
    else:
        manager.backend.hold_modifier("super")
        manager.backend.fake_button_press(1)
        manager.backend.fake_button_release(1)
        manager.backend.release_modifier("super")
    assert manager.c.window.info()["name"] == "above"
    window_by_name(manager.c, "below").keep_above(enable=True)
    assert is_stacked_above(manager, "below", "above")
    assert manager.c.window.info()["name"] == "above"

    if follow_mouse_focus is False:
        manager.c.group.focus_by_name("below")
    else:
        manager.backend.hold_modifier("super")
        manager.backend.fake_button_press(1)
        manager.backend.fake_button_release(1)
        manager.backend.release_modifier("super")
    assert manager.c.window.info()["name"] == "below"
    window_by_name(manager.c, "below").keep_below(enable=True)
    assert is_stacked_above(manager, "above", "below")
    assert manager.c.window.info()["name"] == "below"

    if follow_mouse_focus is False:
        manager.c.group.focus_by_name("above")
    else:
        manager.backend.hold_modifier("super")
        manager.backend.fake_button_press(1)
        manager.backend.fake_button_release(1)
        manager.backend.release_modifier("super")
    assert manager.c.window.info()["name"] == "above"
    window_by_name(manager.c, "below").bring_to_front()
    assert is_stacked_above(manager, "below", "above")
    assert manager.c.window.info()["name"] == "above"


@follow_mouse_focus_config
def test_follow_mouse_focus_after_change_group(manager, follow_mouse_focus):
    """
    When changing group places the pointer over a window that isn't focused,
    click or drag bindings should focus the window and perform the specified
    action if follow_mouse_focus is not False
    """

    manager.test_window("left")
    manager.c.window.set_position_floating(50, 50)
    manager.c.window.set_size_floating(100, 100)

    manager.test_window("right")
    manager.c.window.set_position_floating(150, 50)
    manager.c.window.set_size_floating(100, 100)
    assert manager.c.window.info()["name"] == "right"

    # Move over the "right" window
    manager.backend.fake_motion(155, 55)

    # Change group, move over "left" window, and change back to initial group
    manager.c.group["b"].toscreen()
    manager.backend.fake_motion(55, 55)
    manager.c.group["a"].toscreen()

    # Window "right" should maintain focus
    assert manager.c.window.info()["name"] == "right"

    # Send fake Drag event
    manager.backend.hold_modifier("super")
    manager.backend.fake_button_press(3)
    manager.backend.fake_motion(65, 65)
    manager.backend.fake_button_release(3)
    manager.backend.release_modifier("super")

    info = manager.c.window.info()
    if follow_mouse_focus is False:
        # "right" window should maintain focus and move
        assert manager.c.window.info()["name"] == "right"
        assert (info["x"], info["y"]) == (160, 60)  # 150 + 10, 50 + 10
    if follow_mouse_focus is not False:
        # "left" window should take focus and move
        assert manager.c.window.info()["name"] == "left"
        assert (info["x"], info["y"]) == (60, 60)  # 50 + 10, 50 + 10
