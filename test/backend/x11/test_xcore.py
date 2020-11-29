from libqtile.backend.x11 import core


def test_keys(display):
    assert "a" in core.get_keys()
    assert "shift" in core.get_modifiers()


def test_no_two_qtiles(manager):
    try:
        core.Core(manager.display).finalize()
    except core.ExistingWMException:
        pass
    else:
        raise Exception("expected an error on multiple qtiles connecting")
