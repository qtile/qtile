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
