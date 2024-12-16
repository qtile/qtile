import pytest

from libqtile import bar, config, hook, layout, log_utils, resources, widget
from libqtile.confreader import Config
from test.conftest import BareConfig, dualmonitor
from test.layouts.layout_utils import assert_focused, assert_unfocused
from test.test_manager import ManagerConfig

bare_config = pytest.mark.parametrize("manager", [BareConfig], indirect=True)


@bare_config
def test_info(manager):
    """
    Checks each backend Window implementation provides the required information.
    """
    manager.test_window("one")
    manager.c.sync()
    info = manager.c.window.info()
    assert info["name"] == "one"
    assert info["group"] == "a"
    assert info["wm_class"][0] == "TestWindow"
    assert "x" in info
    assert "y" in info
    assert "width" in info
    assert "height" in info
    assert "id" in info


@bare_config
def test_is_visible_hidden(manager):
    """
    Test Window#is_visible() with "hidden" (aka layout calls client.hide())
    windows.
    """
    manager.test_window("one")
    assert_focused(manager, "one")

    assert manager.c.window.is_visible()
    manager.c.window.toggle_minimize()
    assert not manager.c.window.is_visible()
    manager.c.window.toggle_minimize()
    assert manager.c.window.is_visible()


@bare_config
def test_is_visible_minimized(manager):
    """
    Test Window#is_visible() with "minized" (aka floating or other
    minimization).
    """
    manager.test_window("one")
    one_id = manager.c.window.info()["id"]
    manager.test_window("two")
    two_id = manager.c.window.info()["id"]

    assert_focused(manager, "two")
    assert manager.c.window.is_visible()
    assert not manager.c.window[one_id].is_visible()

    manager.c.layout.up()
    assert_focused(manager, "one")
    assert manager.c.window.is_visible()
    assert not manager.c.window[two_id].is_visible()


@bare_config
def test_margin(manager):
    manager.test_window("one")

    # No margin
    manager.c.window.place(10, 20, 50, 60, 0, "000000")
    assert manager.c.window.info()["x"] == 10
    assert manager.c.window.info()["y"] == 20
    assert manager.c.window.info()["width"] == 50
    assert manager.c.window.info()["height"] == 60

    # Margin as int
    manager.c.window.place(10, 20, 50, 60, 0, "000000", margin=8)
    assert manager.c.window.info()["x"] == 18
    assert manager.c.window.info()["y"] == 28
    assert manager.c.window.info()["width"] == 34
    assert manager.c.window.info()["height"] == 44

    # Margin as list
    manager.c.window.place(10, 20, 50, 60, 0, "000000", margin=[2, 4, 8, 10])
    assert manager.c.window.info()["x"] == 20
    assert manager.c.window.info()["y"] == 22
    assert manager.c.window.info()["width"] == 36
    assert manager.c.window.info()["height"] == 50


@bare_config
def test_no_size_hint(manager):
    manager.test_window("one")
    manager.c.window.enable_floating()
    assert manager.c.window.info()["width"] == 100
    assert manager.c.window.info()["height"] == 100

    manager.c.window.set_size_floating(50, 50)
    assert manager.c.window.info()["width"] == 50
    assert manager.c.window.info()["height"] == 50

    manager.c.window.set_size_floating(200, 200)
    assert manager.c.window.info()["width"] == 200
    assert manager.c.window.info()["height"] == 200


@bare_config
def test_togroup_toggle(manager):
    manager.test_window("one")
    assert manager.c.group.info()["name"] == "a"  # Start on "a"
    assert manager.c.get_groups()["a"]["focus"] == "one"
    assert manager.c.get_groups()["b"]["focus"] is None
    manager.c.window.togroup("b", switch_group=True)
    assert manager.c.group.info()["name"] == "b"  # Move the window and switch to "b"
    assert manager.c.get_groups()["a"]["focus"] is None
    assert manager.c.get_groups()["b"]["focus"] == "one"
    manager.c.window.togroup("b", switch_group=True)
    assert manager.c.group.info()["name"] == "b"  # Does not toggle by default
    assert manager.c.get_groups()["a"]["focus"] is None
    assert manager.c.get_groups()["b"]["focus"] == "one"
    manager.c.window.togroup("b", switch_group=True, toggle=True)
    assert (
        manager.c.group.info()["name"] == "a"
    )  # Explicitly toggling moves the window and switches to "a"
    assert manager.c.get_groups()["a"]["focus"] == "one"
    assert manager.c.get_groups()["b"]["focus"] is None
    manager.c.window.togroup("b", switch_group=True, toggle=True)
    manager.c.window.togroup("b", switch_group=True, toggle=True)
    assert manager.c.group.info()["name"] == "a"  # Toggling twice roundtrips between the two
    assert manager.c.get_groups()["a"]["focus"] == "one"
    assert manager.c.get_groups()["b"]["focus"] is None
    manager.c.window.togroup("b", toggle=True)
    assert (
        manager.c.group.info()["name"] == "a"
    )  # Toggling without switching only moves the window
    assert manager.c.get_groups()["a"]["focus"] is None
    assert manager.c.get_groups()["b"]["focus"] == "one"


class BringFrontClickConfig(ManagerConfig):
    bring_front_click = True


class BringFrontClickFloatingOnlyConfig(ManagerConfig):
    bring_front_click = "floating_only"


@pytest.fixture
def bring_front_click(request):
    return request.param


@pytest.mark.parametrize(
    "manager, bring_front_click",
    [
        (ManagerConfig, False),
        (BringFrontClickConfig, True),
        (BringFrontClickFloatingOnlyConfig, "floating_only"),
    ],
    indirect=True,
)
def test_bring_front_click(manager, bring_front_click):
    manager.c.group.setlayout("tile")
    # this is a tiled window.
    manager.test_window("one")

    manager.test_window("two")
    manager.c.window.set_position_floating(50, 50)
    manager.c.window.set_size_floating(50, 50)

    manager.test_window("three")
    manager.c.window.set_position_floating(150, 50)
    manager.c.window.set_size_floating(50, 50)

    wids = [x["id"] for x in manager.c.windows()]
    names = [x["name"] for x in manager.c.windows()]

    assert names == ["one", "two", "three"]
    wins = manager.backend.get_all_windows()
    assert wins.index(wids[0]) < wins.index(wids[1]) < wins.index(wids[2])

    # Click on window two
    manager.backend.fake_click(55, 55)
    assert manager.c.window.info()["name"] == "two"
    wins = manager.backend.get_all_windows()
    if bring_front_click:
        assert wins.index(wids[0]) < wins.index(wids[2]) < wins.index(wids[1])
    else:
        assert wins.index(wids[0]) < wins.index(wids[1]) < wins.index(wids[2])

    # Click on window one
    manager.backend.fake_click(10, 10)
    assert manager.c.window.info()["name"] == "one"
    wins = manager.backend.get_all_windows()
    if bring_front_click == "floating_only":
        assert wins.index(wids[0]) < wins.index(wids[2]) < wins.index(wids[1])
    elif bring_front_click:
        assert wins.index(wids[2]) < wins.index(wids[1]) < wins.index(wids[0])
    else:
        assert wins.index(wids[0]) < wins.index(wids[1]) < wins.index(wids[2])


@dualmonitor
@bare_config
def test_center_window(manager):
    """Check that floating windows are centered correctly."""
    manager.test_window("one")

    manager.c.window.set_position_floating(50, 50)
    manager.c.window.set_size_floating(200, 100)
    info = manager.c.window.info()
    assert info["x"] == 50
    assert info["y"] == 50
    assert info["width"] == 200
    assert info["height"] == 100

    manager.c.window.center()
    info = manager.c.window.info()
    assert info["x"] == (800 - 200) / 2  # (screen width - window width) / 2
    assert info["y"] == (600 - 100) / 2  # (screen height - window height) / 2
    assert info["width"] == 200
    assert info["height"] == 100

    manager.c.window.togroup("b")  # Second screen
    manager.c.to_screen(1)  # Focus screen
    manager.c.group["b"].toscreen()  # Make sure group b is on that screen

    # Second screen is 640x480 at offset (800, 0)
    manager.c.window.center()
    info = manager.c.window.info()
    assert info["x"] == 800 + (640 - 200) / 2  # offset + (screen width - window width) / 2
    assert info["y"] == (480 - 100) / 2  # (screen height - window height) / 2
    assert info["width"] == 200
    assert info["height"] == 100


class PositionConfig(Config):
    auto_fullscreen = True
    groups = [
        config.Group("a"),
        config.Group("b"),
    ]
    # MonadTall supports swap, treetab doesn't
    layouts = [layout.MonadTall(), layout.TreeTab()]
    floating_layout = resources.default_config.floating_layout
    keys = []
    mouse = []
    screens = []
    follow_mouse_focus = False


position_config = pytest.mark.parametrize("manager", [PositionConfig], indirect=True)


@position_config
def test_set_position(manager):
    """Check that windows are positioned correctly."""
    manager.test_window("one")

    # Get first pane coords
    info = manager.c.window.info()
    coords = info["x"], info["y"]
    manager.test_window("two")

    # Get second pane coords
    info = manager.c.window.info()
    two_coords = info["x"], info["y"]

    # We should have client one and two in the layout
    assert manager.c.layout.info()["clients"] == ["one", "two"]

    # Set the position to the first window pane
    # We need to also set the pointer coords as the function uses them
    manager.c.eval(f"self.core.warp_pointer({coords[0]}, {coords[1]})")
    manager.c.window.set_position(coords[0], coords[1])

    # Now they should be swapped
    assert manager.c.layout.info()["clients"] == ["two", "one"]

    # Swap back to the second pane
    manager.c.eval(f"self.core.warp_pointer({two_coords[0]}, {two_coords[1]})")
    manager.c.window.set_position(two_coords[0], two_coords[1])

    # Now they should be back to original
    assert manager.c.layout.info()["clients"] == ["one", "two"]

    # Test with a layout which doesn't support swap right now (TreeTab)
    manager.c.layout.next()
    manager.c.eval(f"self.core.warp_pointer({coords[0]}, {coords[1]})")
    manager.c.window.set_position(coords[0], coords[1])

    # Now they should be the same
    assert manager.c.layout.info()["clients"] == ["one", "two"]

    # Now test with floating
    manager.c.window.enable_floating()
    manager.c.window.set_position(50, 50)
    info = manager.c.window.info()

    # Check if the position matches
    assert info["x"] == 50
    assert info["y"] == 50

    # Also check if there is only one client now
    assert len(manager.c.layout.info()["clients"]) == 1


class WindowNameConfig(BareConfig):
    screens = [
        config.Screen(
            bottom=bar.Bar(
                [
                    widget.WindowName(),
                ],
                20,
            ),
        ),
    ]
    layouts = [layout.Columns()]


@pytest.mark.parametrize("manager", [WindowNameConfig], indirect=True)
def test_focus_switch(manager):
    def _wnd(name):
        return manager.c.window[{w["name"]: w["id"] for w in manager.c.windows()}[name]]

    manager.test_window("One")
    manager.test_window("Two")

    assert manager.c.widget["windowname"].info()["text"] == "Two"

    _wnd("One").focus()
    assert manager.c.widget["windowname"].info()["text"] == "One"


def set_steal_focus(win):
    if win.name != "three":
        win.can_steal_focus = False


@pytest.fixture
def hook_fixture():
    log_utils.init_log()
    yield
    hook.clear()


@pytest.mark.usefixtures("hook_fixture")
def test_can_steal_focus(manager_nospawn):
    """
    Test Window.can_steal_focus.
    """

    class AntiFocusStealConfig(BareConfig):
        hook.subscribe.client_new(set_steal_focus)

    manager_nospawn.start(AntiFocusStealConfig)
    manager_nospawn.test_window("one")
    assert_unfocused(manager_nospawn, "one")

    manager_nospawn.test_window("two")
    assert_unfocused(manager_nospawn, "one")
    assert_unfocused(manager_nospawn, "two")

    manager_nospawn.test_window("three")
    assert_focused(manager_nospawn, "three")
