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


@bare_config
def test_window_opacity(wmanager):
    # 1. Spawn a fake window
    wmanager.test_window("one")
    # 2. Check the default opacity
    assert wmanager.c.window.info()["opacity"] == 1.0
    # 3. Change the opacity using the IPC command
    wmanager.c.window.set_opacity(0.5)
    assert wmanager.c.window.info()["opacity"] == 0.5
    # 5. Spawn a second window to ensure the compositor doesn't crash
    wmanager.test_window("two")
    assert wmanager.c.window.info()["opacity"] == 1.0  # The NEW window is 1.0
    # Test multi window consistency
    wmanager.c.window.set_opacity(0.2)
    assert window_by_name(wmanager.c, "two").info()["opacity"] == 0.2  #
    assert window_by_name(wmanager.c, "one").info()["opacity"] == 0.5


@bare_config
def test_window_opacity_commands(wmanager):
    wmanager.test_window("one")
    # 1. Initial state should be 1.0
    assert wmanager.c.window.info()["opacity"] == 1.0

    # 2. Test explicit out-of-bounds (High)
    wmanager.c.window.set_opacity(5.0)
    assert wmanager.c.window.info()["opacity"] == 1.0

    # 3. Test explicit out-of-bounds (Low)
    # The base class IPC command clamps at 0.1, not 0.0!
    wmanager.c.window.set_opacity(-1.0)
    assert wmanager.c.window.info()["opacity"] == pytest.approx(0.1)

    # 4. Set to a normal value for stepping
    wmanager.c.window.set_opacity(0.5)
    assert wmanager.c.window.info()["opacity"] == 0.5

    # 5. Test single steps
    wmanager.c.window.up_opacity()
    assert wmanager.c.window.info()["opacity"] == pytest.approx(0.6)

    wmanager.c.window.down_opacity()
    assert wmanager.c.window.info()["opacity"] == pytest.approx(0.5)

    # 6. Break it: Spam down_opacity way past 0.1
    for _ in range(10):
        wmanager.c.window.down_opacity()

    # Should be firmly clamped at 0.1
    assert wmanager.c.window.info()["opacity"] == pytest.approx(0.1)

    # 7. Break it: Spam up_opacity way past 1.0
    for _ in range(15):
        wmanager.c.window.up_opacity()

    # Should be firmly clamped at 1.0
    assert wmanager.c.window.info()["opacity"] == pytest.approx(1.0)
