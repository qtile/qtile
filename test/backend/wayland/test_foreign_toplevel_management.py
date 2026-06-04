import pytest

from test.conftest import dualmonitor

pytestmark = pytest.mark.parametrize("test_client", ["ftl-manager"], indirect=True)


def make_line(title, activated=False, fullscreen=False, maximized=False, minimized=False):
    def yn(value):
        return "Y" if value else "N"

    return (
        f"title:{title} app_id:TestWindow activated:{yn(activated)} "
        f"fullscreen:{yn(fullscreen)} maximized:{yn(maximized)} "
        f"minimized:{yn(minimized)}"
    )


def get_window(title, wmanager):
    wins = wmanager.c.windows()
    for w in wins:
        if w["name"] == title:
            return wmanager.c.window[w["id"]]

    assert False


def test_ftl_state(wmanager, test_client):
    """Test that client is notified about client state."""
    wmanager.test_window("window1")
    win1 = get_window("window1", wmanager)
    lines = test_client.send_read_until("list", "OK")
    assert make_line("window1", activated=True) in lines

    # Test maximize
    win1.toggle_maximize()
    lines = test_client.send_read_until("list", "OK")
    assert make_line("window1", activated=True, maximized=True) in lines
    win1.toggle_maximize()
    lines = test_client.send_read_until("list", "OK")
    assert make_line("window1", activated=True) in lines

    # Test minimize (NB window is not focused when minimized)
    win1.toggle_minimize()
    lines = test_client.send_read_until("list", "OK")
    assert make_line("window1", activated=False, minimized=True) in lines
    win1.toggle_minimize()
    lines = test_client.send_read_until("list", "OK")
    assert make_line("window1", activated=True) in lines

    # Test fullscreen
    win1.toggle_fullscreen()
    lines = test_client.send_read_until("list", "OK")
    assert make_line("window1", activated=True, fullscreen=True) in lines
    win1.toggle_fullscreen()
    lines = test_client.send_read_until("list", "OK")
    assert make_line("window1", activated=True) in lines


def test_focus_state(wmanager, test_client):
    wmanager.test_window("window1")
    wmanager.test_window("window2")
    win1 = get_window("window1", wmanager)
    win2 = get_window("window2", wmanager)

    lines = test_client.send_read_until("list", "OK")
    assert make_line("window1") in lines
    assert make_line("window2", activated=True) in lines

    win1.focus()
    lines = test_client.send_read_until("list", "OK")
    assert make_line("window1", activated=True) in lines
    assert make_line("window2") in lines

    win2.focus()
    lines = test_client.send_read_until("list", "OK")
    assert make_line("window1") in lines
    assert make_line("window2", activated=True) in lines


def test_client_set_state(wmanager, test_client):
    wmanager.test_window("window1")
    win1 = get_window("window1", wmanager)
    lines = test_client.send_read_until("list", "OK")
    assert make_line("window1", activated=True) in lines

    test_client.assert_ok("fullscreen window1")
    assert win1.info()["fullscreen"]
    test_client.assert_ok("fullscreen window1")
    assert not win1.info()["fullscreen"]

    test_client.assert_ok("maximize window1")
    assert win1.info()["maximized"]
    test_client.assert_ok("maximize window1")
    assert not win1.info()["maximized"]

    test_client.assert_ok("minimize window1")
    assert win1.info()["minimized"]
    test_client.assert_ok("minimize window1")
    assert not win1.info()["minimized"]


def test_client_focus(wmanager, test_client):
    def assert_focused(name):
        assert wmanager.c.window.info()["name"] == name

    wmanager.test_window("window1")
    wmanager.test_window("window2")

    assert_focused("window2")

    test_client.assert_ok("activate window1")
    assert_focused("window1")

    test_client.assert_ok("activate window2")
    assert_focused("window2")


@dualmonitor
def test_output_enter_leave(wmanager, test_client):
    wmanager.test_window("window1")
    win1 = get_window("window1", wmanager)

    test_client.assert_ok("output_reset window1")
    win1.set_size_floating(200, 200)
    win1.set_position_floating(700, 100)
    lines = test_client.send_read_until("output_enter window1", "OK")
    assert "output_enter: HEADLESS-1" in lines
    test_client.assert_error("output_leave window1", "output_leave message not received")
    win1.set_position(900, 100)
    lines = test_client.send_read_until("output_leave window1", "OK")
    assert "output_leave: HEADLESS-2" in lines
