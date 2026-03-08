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
def test_layer_floats_kept_above(wmanager, floats_kept_above):
    """Use keep above layer to keep floating windows above tiled"""

    wmanager.test_window("one", floating=True)
    if floats_kept_above:
        assert window_by_name(wmanager.c, "one").layer() == lib.LAYER_KEEPABOVE
    else:
        assert window_by_name(wmanager.c, "one").layer() == lib.LAYER_LAYOUT

    window_by_name(wmanager.c, "one").toggle_floating()
    assert window_by_name(wmanager.c, "one").layer() == lib.LAYER_LAYOUT


@layers_config
def test_layer_bring_to_front(wmanager):
    """Move windows to bring to front layer"""
    # TODO: This test should be extended to also test mechanisms for returning
    # windows from bring to front layer

    wmanager.test_window("one")
    assert window_by_name(wmanager.c, "one").layer() == lib.LAYER_LAYOUT

    wmanager.c.window.bring_to_front()
    assert window_by_name(wmanager.c, "one").layer() == lib.LAYER_BRINGTOFRONT


# TODO: Add test for bring_front_click
