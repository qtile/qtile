import pytest

from libqtile.bar import Bar
from libqtile.config import Screen
from test.backend.wayland.helpers import count_node_types, find_layer
from test.conftest import dualmonitor
from test.helpers import BareConfig, Retry

pytestmark = pytest.mark.parametrize("test_client", ["layer-shell"], indirect=True)


class LSConfigTop(BareConfig):
    screens = [Screen(top=Bar([], 24))]


class LSConfigBottom(BareConfig):
    screens = [Screen(bottom=Bar([], 24))]


class LSConfigLeft(BareConfig):
    screens = [Screen(left=Bar([], 24))]


class LSConfigRight(BareConfig):
    screens = [Screen(right=Bar([], 24))]


@pytest.mark.parametrize(
    "anchors,diffs",
    [
        (["TLR"], (0, 40, 0, -40)),
        (["BLR"], (0, 0, 0, -40)),
        (["TBL"], (40, 0, -40, 0)),
        (["TBR"], (0, 0, -40, 0)),
        (["TLR", "BLR"], (0, 40, 0, -80)),
        (["TBL", "TBR"], (40, 0, -80, 0)),
        (["TBL", "TBR", "TLR"], (40, 40, -80, -40)),
        (["TBL", "TBR", "BLR"], (40, 0, -80, -40)),
        (["TBL", "TLR", "BLR"], (40, 40, -40, -80)),
        (["TBR", "TLR", "BLR"], (0, 40, -40, -80)),
        (["TLR", "BLR", "TBL", "TBR"], (40, 40, -80, -80)),
    ],
)
def test_layer_shell_exclusive_space_window(test_client, wmanager, anchors, diffs):
    """Test that window position is adjusted for exclusive space."""

    @Retry(ignore_exceptions=(AssertionError,))
    def wait_for_window():
        assert len(wmanager.c.windows()) == 1

    def xywh():
        info = wmanager.c.window.info()
        x = info["x"]
        y = info["y"]
        w = info["width"]
        h = info["height"]
        return x, y, w, h

    wmanager.test_window("win")
    wait_for_window()
    orig = xywh()

    clones = []
    for anchor in anchors:
        clone = test_client.clone()
        clone.assert_ok(f"anchor {anchor}")
        clone.assert_ok("show")
        clones.append(clone)

    # Calculated expected x, y, w, h by applying diffs to original position
    expected = tuple(a + b for a, b in zip(orig, diffs))
    moved = xywh()
    assert moved == expected

    # Check space is restored correctly
    for clone in clones:
        clone.assert_ok("close")

    assert xywh() == orig


@pytest.mark.parametrize(
    "wmanager,bar_position,anchors,offsets",
    [
        (LSConfigTop, "top", "TLR", (0, 40)),
        (LSConfigBottom, "bottom", "BLR", (0, -40)),
        (LSConfigLeft, "left", "LTB", (40, 0)),
        (LSConfigRight, "right", "RTB", (-40, 0)),
    ],
    indirect=["wmanager"],
)
def test_layer_shell_exclusive_space_bar(test_client, wmanager, bar_position, anchors, offsets):
    """Test that bar position is adjusted for exclusive space."""
    bar = wmanager.c.bar[bar_position].info()
    orig_x, orig_y = bar["x"], bar["y"]
    test_client.assert_ok(f"anchor {anchors}")
    test_client.assert_ok("show")

    bar = wmanager.c.bar[bar_position].info()
    offsetx, offsety = offsets
    assert bar["x"] == orig_x + offsetx
    assert bar["y"] == orig_y + offsety

    test_client.assert_ok("close")
    bar = wmanager.c.bar[bar_position].info()
    assert (bar["x"], bar["y"]) == (orig_x, orig_y)


@pytest.mark.parametrize("layer_name", ["top", "overlay", "background", "bottom"])
def test_layer_shell_layer(test_client, wmanager, layer_name):
    """Test that qtile respects layer shell layer requew psts"""
    layer = f"LAYER_{layer_name.upper()}"

    def assert_count(num):
        """Count surfaces on the requested layer."""
        stack = find_layer(wmanager.c.core.stacking_info(), layer)
        assert stack
        counts = count_node_types(stack)
        assert counts.get("buffer", 0) == num

    assert_count(0)
    test_client.assert_ok(f"layer {layer_name}")
    test_client.assert_ok("show")
    assert_count(1)


@pytest.mark.parametrize("mode,expected", [("none", False), ("exclusive", True)])
def test_layer_shell_keyboard_interactivity(test_client, wmanager, mode, expected):
    """Test whether the layer surface gets keyboard focus."""

    @Retry(ignore_exceptions=(AssertionError,))
    def wait_for_window():
        assert len(wmanager.c.windows()) == 1

    test_client.assert_ok(f"keyboard {mode}")
    test_client.assert_ok("show")

    test_client.assert_true_or_false("has_keyboard", expected)

    wmanager.test_window("new_client")
    wait_for_window()

    test_client.assert_true_or_false("has_keyboard", expected)


@dualmonitor
def test_layer_surface_commit_after_output_destroy(wmanager, test_client):
    """
    Regression test for a use-after-free in the Wayland layer-shell handling.
    A layer-shell surface keeps a back-pointer to the output it lives on. When the
    output is destroyed, ``qw_output_handle_destroy`` nulls that back-pointer but the
    surface itself outlives the output (the client has not destroyed it yet). If the
    client then commits, ``qw_layer_view_handle_commit`` used to call
    ``qw_output_arrange_layers(layer_view->output)`` with ``output == NULL``, reading
    ``output->full_area`` off a freed/NULL pointer and crashing the compositor.
    The fix makes the commit handler return early when ``output == NULL``.
    """
    test_client.assert_ok("output 1")
    test_client.assert_ok("show")

    # Destroy that output while the layer surface is still mapped on it.
    wmanager.c.core.test_destroy_output(1)
    wmanager.c.sync()

    # Commit again: this reaches the commit handler with the now-freed output.
    # Pre-fix, the compositor segfaults here.
    test_client.assert_ok("send_commit")

    # The client is still alive and the compositor still answers IPC, i.e. it did
    # not crash while handling the post-destroy commit.
    test_client.assert_ok("status")
    assert wmanager.c.core.eval("1 + 1") == "2"
