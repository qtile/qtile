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
import logging

import pytest

from libqtile.extension.command_set import CommandSet
from libqtile.log_utils import init_log, logger


@pytest.fixture
def fake_qtile():
    class FakeQtile:
        def cmd_spawn(self, value):
            logger.warning(value)

    yield FakeQtile()


@pytest.fixture
def log_extension_output(monkeypatch):
    init_log(logging.WARNING, log_path=None, log_color=False)

    def fake_popen(cmd, *args, **kwargs):
        class PopenObj:
            def communicate(self, value_in, *args):
                if value_in.startswith(b"missing"):
                    return [b"something_else", None]
                else:
                    return [value_in, None]

        return PopenObj()

    monkeypatch.setattr("libqtile.extension.base.Popen", fake_popen)

    yield


@pytest.mark.usefixtures("log_extension_output")
def test_command_set_valid_command(caplog, fake_qtile):
    """Extension should run pre-commands and selected command."""
    extension = CommandSet(pre_commands=["run pre-command"], commands={"key": "run testcommand"})
    extension._configure(fake_qtile)
    extension.run()

    assert caplog.record_tuples == [
        ("libqtile", logging.WARNING, "run pre-command"),
        ("libqtile", logging.WARNING, "run testcommand"),
    ]


@pytest.mark.usefixtures("log_extension_output")
def test_command_set_invalid_command(caplog, fake_qtile):
    """Where the key is not in "commands", no command will be run."""
    extension = CommandSet(
        pre_commands=["run pre-command"], commands={"missing": "run testcommand"}
    )
    extension._configure(fake_qtile)
    extension.run()

    assert caplog.record_tuples == [("libqtile", logging.WARNING, "run pre-command")]
