from libqtile.backend.x11 import xcore


def test_keys(manager_nospawn):
    xc = xcore.XCore(manager_nospawn.display)
    assert "a" in xc.get_keys()
    assert "shift" in xc.get_modifiers()


def test_no_two_qtiles(manager):
    try:
        xcore.XCore(manager.display)
    except xcore.ExistingWMException:
        pass
    else:
        raise Exception("excpected an error on multiple qtiles connecting")
