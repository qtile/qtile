import pytest

from ..conftest import BareConfig
from libqtile.core import xcore


@pytest.mark.parametrize("qtile", [BareConfig], indirect=True)
def test_keys(qtile):
    xc = xcore.XCore()
    assert "a" in xc.get_keys()
    assert "shift" in xc.get_modifiers()
