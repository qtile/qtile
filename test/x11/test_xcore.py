from libqtile.backend.x11 import xcore


def test_keys(xephyr):
    xc = xcore.XCore()
    assert "a" in xc.get_keys()
    assert "shift" in xc.get_modifiers()
