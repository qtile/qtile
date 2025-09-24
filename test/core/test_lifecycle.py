import pytest

from libqtile.core.lifecycle import Behavior, LifeCycle
from libqtile.log_utils import init_log


def fake_os_execv(executable, args):
    assert args == [
        "arg1",
        "arg2",
        "--no-spawn",
        "--with-state=/tmp/test/fake_statefile",
    ]


def no_op(*args, **kwargs):
    pass


@pytest.fixture
def patched_lifecycle(monkeypatch):
    init_log()
    monkeypatch.setattr("libqtile.core.lifecycle.sys.argv", ["arg1", "arg2"])
    monkeypatch.setattr("libqtile.core.lifecycle.atexit.register", no_op)
    monkeypatch.setattr("libqtile.core.lifecycle.os.execv", fake_os_execv)
    yield LifeCycle()


def test_restart_behaviour(patched_lifecycle, caplog):
    patched_lifecycle.behavior = Behavior.RESTART
    patched_lifecycle.state_file = "/tmp/test/fake_statefile"
    patched_lifecycle._atexit()
    assert caplog.record_tuples == [("libqtile", 30, "Restarting Qtile with os.execv(...)")]


def test_terminate_behavior(patched_lifecycle, caplog):
    patched_lifecycle.behavior = Behavior.TERMINATE
    patched_lifecycle._atexit()
    assert caplog.record_tuples == [("libqtile", 30, "Qtile will now terminate")]


def test_none_behavior(patched_lifecycle, caplog):
    patched_lifecycle.behavior = Behavior.NONE
    patched_lifecycle._atexit()
    assert caplog.record_tuples == []
