from libqtile.backend.x11 import xcore


def test_keys(qtile_nospawn):
    xc = xcore.XCore(qtile_nospawn.display)
    assert "a" in xc.get_keys()
    assert "shift" in xc.get_modifiers()


def test_no_two_qtiles(qtile):
    try:
        xcore.XCore(qtile.display)
    except xcore.ExistingWMException:
        pass
    else:
        raise Exception("excpected an error on multiple qtiles connecting")
