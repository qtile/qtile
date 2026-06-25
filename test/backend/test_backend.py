import pytest

from libqtile.backend import detect_backend, get_core
from libqtile.utils import QtileError


def test_get_core_bad():
    with pytest.raises(QtileError):
        get_core("NonBackend").finalize()


@pytest.mark.parametrize(
    "env,expected",
    [
        ({"XDG_SESSION_TYPE": "wayland"}, "wayland"),
        ({"XDG_SESSION_TYPE": "x11"}, "x11"),
        ({"XDG_SESSION_TYPE": "wayland", "DISPLAY": ":0"}, "wayland"),
        ({"DISPLAY": ":0"}, "x11"),
        ({"XDG_SESSION_TYPE": "tty", "DISPLAY": ":0"}, "x11"),
        ({}, "wayland"),
        ({"WAYLAND_DISPLAY": "wayland-0"}, "wayland"),
    ],
)
def test_detect_backend(monkeypatch, env, expected):
    for var in ("XDG_SESSION_TYPE", "WAYLAND_DISPLAY", "DISPLAY"):
        monkeypatch.delenv(var, raising=False)
    for var, value in env.items():
        monkeypatch.setenv(var, value)
    assert detect_backend() == expected
