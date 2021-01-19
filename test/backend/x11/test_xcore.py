from libqtile.backend.x11 import core


def test_keys(manager_nospawn):
    xc = core.Core(manager_nospawn.display)
    try:
        assert "a" in xc.get_keys()
        assert "shift" in xc.get_modifiers()
    finally:
        xc.finalize()


def test_no_two_qtiles(manager):
    try:
        core.Core(manager.display).finalize()
    except core.ExistingWMException:
        pass
    else:
        raise Exception("expected an error on multiple qtiles connecting")
