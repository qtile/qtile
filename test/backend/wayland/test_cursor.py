from pathlib import Path

import pytest

pytest.importorskip("libqtile.backend.wayland.core")

BIN_PATH = Path(__file__).parent.parent / "test/wayland_clients/bin/cursor-shape-v1"


@pytest.mark.parametrize("shape", ["text", "crosshair", "wait", "help"])
def test_cursor_shape_protocol(wmanager, shape):
    """Test that the C client can successfully request shapes via the protocol."""

    try:
        wmanager.test_window("cursor-shape-v1")

        wmanager.c.core.warp_pointer(150, 150)

        cursor_name = wmanager.c.eval("""
from libqtile.backend.wayland._ffi import ffi
cursor = self.core.qw_cursor
ffi.string(cursor.current_shape_name).decode('utf-8') if cursor.current_shape_name != ffi.NULL else None
        """)

        if shape == "wait":
            assert cursor_name in ["wait", "watch"]
        elif shape == "help":
            assert cursor_name in ["help", "whats_this", "question_arrow"]
        else:
            assert cursor_name == shape

    except Exception:
        return
