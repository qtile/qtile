import pytest

from libqtile.backend import get_core
from libqtile.utils import QtileError


def test_get_core_x11(manager_nospawn):
    get_core('x11', manager_nospawn.display).finalize()


def test_get_core_bad(manager_nospawn):
    with pytest.raises(QtileError):
        get_core("NonBackend").finalize()
