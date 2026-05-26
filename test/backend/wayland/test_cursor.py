from pathlib import Path

import pytest

from test.helpers import Retry

CLIENT_PATH = Path(__file__) / ".." / ".." / ".." / "wayland_clients" / "bin"
CURSOR_CLIENT = CLIENT_PATH / "cursor-shape-v1"


@pytest.mark.parametrize("shape", ["crosshair", "text", "wait", "help", "grab"])
def test_cursor_shape_protocol(wmanager, shape):
    """Test that the C client can successfully request shapes via the protocol."""

    @Retry(ignore_exceptions=(AssertionError,))
    def wait_for_window():
        assert len(wmanager.c.windows()) > 0

    def cursor_name():
        return wmanager.c.core.get_cursor_shape_v1()

    @Retry(ignore_exceptions=(AssertionError,))
    def wait_for_cursor():
        assert cursor_name() != "default"

    wmanager.c.spawn(f"{CURSOR_CLIENT.resolve().as_posix()} -c {shape} -d")
    wait_for_window()
    wmanager.c.window.set_position_floating(150, 150)

    # Cursor is outside window so should be default
    wmanager.c.core.eval("self.warp_pointer(0, 0, motion=True)")
    assert cursor_name() == "default"

    # Move cursor inside test client window
    wmanager.c.core.eval("self.warp_pointer(200, 200, motion=True)")
    wmanager.c.core.eval("self.flush()")
    wait_for_cursor()
    cursor = cursor_name()

    if shape == "wait":
        assert cursor in ["wait", "watch"]
    elif shape == "help":
        assert cursor in ["help", "whats_this", "question_arrow"]
    else:
        assert cursor == shape
