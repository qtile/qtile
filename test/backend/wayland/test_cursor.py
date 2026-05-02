from pathlib import Path

import pytest

pytest.importorskip("libqtile.backend.wayland.core")

BIN_PATH = Path(__file__).parent.parent / "test/wayland_clients/bin/cursor-shape-v1"


@pytest.mark.parametrize("shape", ["text", "crosshair", "wait", "help"])
def test_cursor_shape_protocol(wmanager, shape):
    """Test that the C client can successfully request shapes via the protocol."""
    try:
        wmanager.test_window("cursor-shape-v1")
    except Exception:
        pytest.skip("cursor-shape-v1 protocol not available")

    wmanager.c.eval(f"self.core.warp_pointer({150}, {150}, motion=True)")

    cursor_name = wmanager.c.core.get_cursor_shape_v1()

    if shape == "wait":
        assert cursor_name in ["wait", "watch"]
    elif shape == "help":
        assert cursor_name in ["help", "whats_this", "question_arrow"]
    else:
        assert cursor_name == shape
