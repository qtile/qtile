import pytest

from libqtile.backend import get_core
from libqtile.backend.x11 import core


def test_get_core_x11(display):
    get_core('x11', display).finalize()


def test_keys(display):
    assert "a" in core.get_keys()
    assert "shift" in core.get_modifiers()


def test_no_two_qtiles(xmanager):
    with pytest.raises(core.ExistingWMException):
        core.Core(xmanager.display).finalize()


def test_color_pixel(xmanager):
    (success, e) = xmanager.c.eval("self.core.conn.color_pixel(\"ffffff\")")
    assert success, e
