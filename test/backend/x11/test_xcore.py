from libqtile.backend.x11 import core


def test_keys(manager_nospawn):
    xc = core.Core(manager_nospawn.display)
    assert "a" in xc.get_keys()
    assert "shift" in xc.get_modifiers()


def test_no_two_qtiles(manager):
    try:
        core.Core(manager.display)
    except core.ExistingWMException:
        pass
    else:
        raise Exception("excpected an error on multiple qtiles connecting")
