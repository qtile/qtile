import pytest

from libqtile.backend import get_core
from libqtile.utils import QtileError


def test_get_core_bad():
    with pytest.raises(QtileError):
        get_core("NonBackend").finalize()
