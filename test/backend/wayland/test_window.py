import pytest

import libqtile.layout
from libqtile.backend.wayland._ffi import lib
from test.backend.wayland.conftest import new_layer_client, new_xdg_client
from test.conftest import BareConfig
from test.helpers import window_by_name
from test.layouts.test_common import AllLayoutsConfig

try:
    # Check to see if we should skip layer shell tests
    import gi

    gi.require_version("Gtk", "3.0")
    gi.require_version("GtkLayerShell", "0.1")
    from gi.repository import GtkLayerShell  # noqa: F401

    has_layer_shell = True
except (ImportError, ValueError):
    has_layer_shell = False


class LayersConfig(BareConfig):
    layouts = [
        libqtile.layout.stack.Stack(num_stacks=2),
        libqtile.layout.max.Max(),
    ]
    floats_kept_above = False


bare_config = pytest.mark.parametrize("wmanager", [BareConfig], indirect=True)
layers_config = pytest.mark.parametrize("wmanager", [LayersConfig], indirect=True)
each_layout_config = pytest.mark.parametrize(
    "wmanager", AllLayoutsConfig.generate(), indirect=True
)


@pytest.mark.skipif(not has_layer_shell, reason="GtkLayerShell not available")
@bare_config
def test_info(wmanager):
    """
    Check windows are providing some Wayland-specific info.
    """
    # Regular window via XDG shell
    pid = new_xdg_client(wmanager)
    assert wmanager.c.window.info()["shell"] == "XDG"

    # Regular XDG shell window converted to Static
    wmanager.c.window.static()
    wid = wmanager.c.windows()[0]["id"]
    assert wmanager.c.window[wid].info()["shell"] == "XDG"
    wmanager.kill_window(pid)

    # Static window via layer shell
    pid = new_layer_client(wmanager)
    wid = wmanager.c.windows()[0]["id"]
    assert wmanager.c.window[wid].info()["shell"] == "layer"
    wmanager.kill_window(pid)


class FloatsKeptAboveConfig(LayersConfig):
    floats_kept_above = True


@pytest.fixture
def floats_kept_above(request):
    return request.param


@pytest.mark.parametrize(
    "wmanager, floats_kept_above",
    [(LayersConfig, False), (FloatsKeptAboveConfig, True)],
    indirect=True,
)
def test_floats_not_keep_above(wmanager, floats_kept_above):
    """Floating windows don't change layer"""

    wmanager.test_window("one", floating=True)
    if floats_kept_above:
        assert window_by_name(wmanager.c, "one").layer() == lib.LAYER_KEEPABOVE
    else:
        assert window_by_name(wmanager.c, "one").layer() == lib.LAYER_LAYOUT

    window_by_name(wmanager.c, "one").toggle_floating()
    assert window_by_name(wmanager.c, "one").layer() == lib.LAYER_LAYOUT


@layers_config
def test_bring_to_front(wmanager):
    """Move to/from bring to front layer"""

    wmanager.test_window("one")
    wmanager.test_window("two")
    assert window_by_name(wmanager.c, "two").layer() == lib.LAYER_LAYOUT

    wmanager.c.window.bring_to_front()
    assert window_by_name(wmanager.c, "two").layer() == lib.LAYER_BRINGTOFRONT

    # Focusing another doesn't return window to its layer
    wmanager.c.group.focus_by_name("one")
    assert window_by_name(wmanager.c, "two").layer() == lib.LAYER_BRINGTOFRONT

    # Clicking another doesn't return window to its layer
    wmanager.backend.fake_click(100, 100)
    assert window_by_name(wmanager.c, "two").layer() == lib.LAYER_BRINGTOFRONT

    # Activating another by keybinding doesn't return window to its layer
    wmanager.c.layout.next()
    assert window_by_name(wmanager.c, "two").layer() == lib.LAYER_BRINGTOFRONT
    wmanager.c.group.focus_by_name("one")
    wmanager.c.window.bring_to_front()
    assert window_by_name(wmanager.c, "one").layer() == lib.LAYER_BRINGTOFRONT
    assert window_by_name(wmanager.c, "two").layer() == lib.LAYER_BRINGTOFRONT

    # Minimizing the window removes it from BRINGTOFRONT
    # TODO: This is probably incorrect but we can update later with floating refactor
    wmanager.c.group.focus_by_name("one")
    wmanager.c.window.toggle_minimize()
    assert window_by_name(wmanager.c, "one").layer() == lib.LAYER_LAYOUT
    wmanager.c.window.toggle_minimize()

    # TODO: Changing layout should do what? Currently nothing
    wmanager.c.group.focus_by_name("two")
    assert window_by_name(wmanager.c, "two").layer() == lib.LAYER_BRINGTOFRONT
    wmanager.c.next_layout()
    assert window_by_name(wmanager.c, "two").layer() == lib.LAYER_BRINGTOFRONT
    wmanager.c.prev_layout()

    # TODO: Make floating should do what? Currently returns its layer
    # Again probably incorrect but can update with floating refactor
    assert window_by_name(wmanager.c, "two").layer() == lib.LAYER_BRINGTOFRONT
    wmanager.c.window.enable_floating()
    assert window_by_name(wmanager.c, "two").layer() == lib.LAYER_LAYOUT
    wmanager.c.window.disable_floating()

    # Enabling and toggling bring_to_front
    wmanager.c.group.focus_by_name("one")
    wmanager.c.window.bring_to_front()
    wmanager.c.group.focus_by_name("two")
    wmanager.c.window.bring_to_front(True)
    assert window_by_name(wmanager.c, "one").layer() == lib.LAYER_BRINGTOFRONT
    assert window_by_name(wmanager.c, "two").layer() == lib.LAYER_BRINGTOFRONT
    wmanager.c.window.bring_to_front()
    assert window_by_name(wmanager.c, "two").layer() == lib.LAYER_LAYOUT
    wmanager.c.group.focus_by_name("one")
    wmanager.c.window.bring_to_front(False)
    assert window_by_name(wmanager.c, "one").layer() == lib.LAYER_LAYOUT

    # Return to base layer (which may not always be LAYOUT)
    wmanager.c.window.keep_above(True)
    assert window_by_name(wmanager.c, "one").layer() == lib.LAYER_KEEPABOVE
    wmanager.c.window.bring_to_front(True)
    assert window_by_name(wmanager.c, "one").layer() == lib.LAYER_BRINGTOFRONT
    wmanager.c.window.bring_to_front(False)
    assert window_by_name(wmanager.c, "one").layer() == lib.LAYER_KEEPABOVE


class BringFrontClickConfig(BareConfig):
    floats_kept_above = False
    bring_front_click = True


class BringFrontClickFloatsAboveConfig(BareConfig):
    floats_kept_above = True
    bring_front_click = True


class BringFrontClickFloatingOnlyConfig(BareConfig):
    bring_front_click = "floating_only"


@pytest.fixture
def bring_front_click(request):
    return request.param


@pytest.mark.parametrize(
    "wmanager, bring_front_click, floats_kept_above",
    [
        (LayersConfig, False, False),
        (BringFrontClickConfig, True, False),
        (BringFrontClickFloatsAboveConfig, True, True),
        (BringFrontClickFloatingOnlyConfig, "floating_only", False),
    ],
    indirect=True,
)
def test_bring_front_click(wmanager, bring_front_click, floats_kept_above):
    wmanager.c.group.setlayout("tile")
    # this is a tiled window.
    wmanager.test_window("one")

    wmanager.test_window("two")
    wmanager.c.window.set_position_floating(50, 50)
    wmanager.c.window.set_size_floating(50, 50)

    wmanager.test_window("three")
    wmanager.c.window.set_position_floating(150, 50)
    wmanager.c.window.set_size_floating(50, 50)

    wids = [x["id"] for x in wmanager.c.windows()]
    names = [x["name"] for x in wmanager.c.windows()]

    assert names == ["one", "two", "three"]
    wins = wmanager.backend.get_all_windows()
    assert wins.index(wids[0]) < wins.index(wids[1]) < wins.index(wids[2])

    # Click on window two
    wmanager.backend.fake_click(55, 55)
    assert wmanager.c.window.info()["name"] == "two"
    wins = wmanager.backend.get_all_windows()
    if bring_front_click:
        assert wins.index(wids[0]) < wins.index(wids[2]) < wins.index(wids[1])
    else:
        assert wins.index(wids[0]) < wins.index(wids[1]) < wins.index(wids[2])

    # Click on window one
    wmanager.backend.fake_click(10, 10)
    assert wmanager.c.window.info()["name"] == "one"
    wins = wmanager.backend.get_all_windows()
    if bring_front_click == "floating_only":
        assert wins.index(wids[0]) < wins.index(wids[2]) < wins.index(wids[1])
    elif bring_front_click and floats_kept_above:
        assert wins.index(wids[0]) < wins.index(wids[2]) < wins.index(wids[1])
    elif bring_front_click:
        assert wins.index(wids[2]) < wins.index(wids[1]) < wins.index(wids[0])
    else:
        assert wins.index(wids[0]) < wins.index(wids[1]) < wins.index(wids[2])
