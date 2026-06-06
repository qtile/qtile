import pytest

from test.helpers import Retry

pytestmark = pytest.mark.parametrize("test_client", ["cursor-shape"], indirect=True)


@pytest.mark.parametrize("shape", ["crosshair", "text", "wait", "help", "grab"])
def test_cursor_shape_protocol(test_client, wmanager, shape):
    """Test that the C client can successfully request shapes via the protocol."""

    @Retry(ignore_exceptions=(AssertionError,))
    def wait_for_window():
        assert len(wmanager.c.windows()) > 0

    def cursor_name():
        return wmanager.c.core.get_cursor_shape_v1()

    @Retry(ignore_exceptions=(AssertionError,))
    def wait_for_cursor():
        assert cursor_name() != "default"

    test_client.assert_ok(shape)
    wait_for_window()
    wmanager.c.window.set_position_floating(150, 150)

    # Cursor is outside window so should be default
    wmanager.c.core.eval("self.warp_pointer(0, 0, motion=True)")
    assert cursor_name() == "default"

    # Move cursor inside test client window
    wmanager.c.core.eval("self.warp_pointer(200, 200, motion=True)")
    wmanager.c.core.flush()
    wait_for_cursor()
    cursor = cursor_name()

    if shape == "wait":
        assert cursor in ["wait", "watch"]
    elif shape == "help":
        assert cursor in ["help", "whats_this", "question_arrow"]
    else:
        assert cursor == shape
