import pytest

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


bare_config = pytest.mark.parametrize("wmanager", [BareConfig], indirect=True)
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


class FloatsKeptAboveConfig(BareConfig):
    floats_kept_above = False


@pytest.fixture
def floats_kept_above(request):
    return request.param


@pytest.mark.parametrize(
    "wmanager, floats_kept_above",
    [(BareConfig, True), (FloatsKeptAboveConfig, False)],
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


@each_layout_config
def test_bring_to_front(wmanager):
    """Move to/from bring to front layer"""
    print(wmanager.c.layout.info())

    wmanager.test_window("one")
    wmanager.test_window("two")
    assert window_by_name(wmanager.c, "two").layer() == lib.LAYER_LAYOUT

    wmanager.c.window.bring_to_front()
    assert window_by_name(wmanager.c, "two").layer() == lib.LAYER_BRINGTOFRONT

    # window_by_name(wmanager.c, "one").focus()
    wmanager.c.group.focus_by_name("one")
    assert window_by_name(wmanager.c, "two").layer() == lib.LAYER_LAYOUT

#TODO: Test if clear_focus also returns layer to previous layer

#TODO: What if previous layer is no longer correct?

class BringFrontClickConfig(BareConfig):
    bring_front_click = True


class BringFrontClickFloatingOnlyConfig(BareConfig):
    bring_front_click = "floating_only"


@pytest.fixture
def bring_front_click(request):
    return request.param


@pytest.mark.parametrize(
    "wmanager, bring_front_click",
    [
        (BareConfig, False),
        (BringFrontClickConfig, True),
        (BringFrontClickFloatingOnlyConfig, "floating_only"),
    ],
    indirect=True,
)
def test_floats_bring_front_click(wmanager, bring_front_click):
    """Floating windows move to keep above layer"""

    wmanager.test_window("one")
    wmanager.test_window("two")
    wmanager.c.window.set_position_floating(50, 50)
    wmanager.c.window.set_size_floating(50, 50)

    # Click floating window (two)
    wmanager.backend.fake_click(60, 60)
    if bring_front_click:
        assert window_by_name(wmanager.c, "two").layer() == lib.LAYER_BRINGTOFRONT
    else:
        assert window_by_name(wmanager.c, "two").layer() == lib.LAYER_KEEPABOVE

    # Click tiled window (one)
    wmanager.backend.fake_click(10, 10)
    if bring_front_click == "floating_only":
        assert window_by_name(wmanager.c, "one").layer() == lib.LAYER_LAYOUT
        assert window_by_name(wmanager.c, "two").layer() == lib.LAYER_KEEPABOVE
    elif bring_front_click:
        assert window_by_name(wmanager.c, "one").layer() == lib.LAYER_BRINGTOFRONT
        assert window_by_name(wmanager.c, "two").layer() == lib.LAYER_KEEPABOVE
    else:
        assert window_by_name(wmanager.c, "one").layer() == lib.LAYER_LAYOUT
