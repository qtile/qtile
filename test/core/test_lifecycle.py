# Copyright (c) 2021 elParaguayo
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
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
