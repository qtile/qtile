import pytest

pytestmark = pytest.mark.parametrize("test_client", ["drag-and-drop"], indirect=True)


def _window_center(wmanager):
    win = wmanager.c.windows()[0]
    assert win["width"] == 300
    assert win["height"] == 300
    return win["x"] + win["width"] // 2, win["y"] + win["height"] // 2


def _start_dnd(test_client, wmanager):
    test_client.assert_ok("create")

    x, y = _window_center(wmanager)
    wmanager.backend.fake_motion(x, y)
    wmanager.backend.fake_button_press(1)

    test_client.assert_ok("start_drag")


def test_dnd(test_client, wmanager):
    """Press and release start and end a drag within the window"""
    _start_dnd(test_client, wmanager)

    x, y = _window_center(wmanager)
    wmanager.backend.fake_motion(x + 10, y + 10)
    wmanager.backend.fake_button_release(1)

    test_client.assert_true("wait_drag_end")


def test_dnd_release_outside_start_window(test_client, wmanager):
    """Press and release outside the start window start and end a drag"""
    _start_dnd(test_client, wmanager)

    x, y = _window_center(wmanager)
    wmanager.backend.fake_motion(x + 160, y + 160)
    wmanager.backend.fake_button_release(1)

    test_client.assert_true("wait_drag_end")


def test_dnd_release_after_source_window_unmapped(test_client, wmanager):
    """Window is unmapped after starting drag. The drag should still end

    As an example, when a browser detaches a single tab: the toplevel may be
    unmapped mid-drag, but the release must still reach the seat, otherwise
    the drag is never released.
    """
    _start_dnd(test_client, wmanager)

    # Unmap the source window
    test_client.assert_ok("unmap")

    wmanager.backend.fake_motion(10, 10)
    wmanager.backend.fake_button_release(1)

    test_client.assert_true("wait_drag_end")
