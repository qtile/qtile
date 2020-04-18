import os

import pytest
import xcffib
import xcffib.testing

from libqtile.backend.x11 import xcbq


@pytest.fixture(scope='function', autouse=True)
def xdisplay(request):
    with xcffib.testing.XvfbTest(width=1280, height=720):
        yield os.environ['DISPLAY']


def test_new_window(xdisplay):
    conn = xcbq.Connection(xdisplay)
    win = conn.create_window(1, 2, 640, 480)
    assert isinstance(win, xcbq.Window)
    geom = win.get_geometry()
    assert geom.x == 1
    assert geom.y == 2
    assert geom.width == 640
    assert geom.height == 480
    win.kill_client()
    with pytest.raises(xcffib.ConnectionException):
        win.get_geometry()


def test_net_wm_states(xdisplay):
    conn = xcbq.Connection(xdisplay)
    win = conn.create_window(1, 1, 640, 480)
    assert isinstance(win, xcbq.Window)

    def attr_name(x):
        return x.lstrip('_').lower()

    names = [attr_name(x) for x in xcbq.net_wm_states]

    for name in names:
        val = getattr(win, name)
        assert val is False
        setattr(win, name, True)
        val = getattr(win, name)
        assert val is True

    for name in names:
        assert getattr(win, name) is True

    for name in names:
        setattr(win, name, False)
        val = getattr(win, name)
        assert val is False


def test_masks():
    cfgmasks = xcbq.ConfigureMasks
    d = {'x': 1, 'y': 2, 'width': 640, 'height': 480}
    mask, vals = cfgmasks(**d)
    assert set(vals) == set(d.values())
    with pytest.raises(ValueError):
        mask, vals = cfgmasks(asdf=32, **d)


def test_translate_masks():
    assert xcbq.translate_masks(["shift", "control"])
    assert xcbq.translate_masks([]) == 0
