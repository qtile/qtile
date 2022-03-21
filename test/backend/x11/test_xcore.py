import pytest

from libqtile.backend import get_core
from libqtile.backend.x11 import core
from test.test_manager import ManagerConfig


def test_get_core_x11(display):
    get_core("x11", display).finalize()


def test_keys(display):
    assert "a" in core.get_keys()
    assert "shift" in core.get_modifiers()


def test_no_two_qtiles(xmanager):
    with pytest.raises(core.ExistingWMException):
        core.Core(xmanager.display).finalize()


def test_color_pixel(xmanager):
    (success, e) = xmanager.c.eval('self.core.conn.color_pixel("ffffff")')
    assert success, e


@pytest.mark.parametrize("xmanager", [ManagerConfig], indirect=True)
def test_net_client_list(xmanager, conn):
    def assert_clients(number):
        clients = conn.default_screen.root.get_property("_NET_CLIENT_LIST", unpack=int)
        assert len(clients) == number

    # ManagerConfig has a Bar, which should not appear in _NET_CLIENT_LIST
    assert_clients(0)
    one = xmanager.test_window("one")
    assert_clients(1)
    two = xmanager.test_window("two")
    xmanager.c.window.toggle_minimize()
    three = xmanager.test_window("three")
    xmanager.c.screen.next_group()
    assert_clients(3)  # Minimized windows and windows on other groups are included
    xmanager.kill_window(one)
    xmanager.c.screen.next_group()
    assert_clients(2)
    xmanager.kill_window(three)
    assert_clients(1)
    xmanager.c.screen.next_group()
    one = xmanager.test_window("one")
    assert_clients(2)
    xmanager.c.window.static()  # Static windows are not included
    assert_clients(1)
    xmanager.kill_window(two)
    assert_clients(0)
