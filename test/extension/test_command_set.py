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
import asyncio
import logging

import pytest

from libqtile.extension.command_set import CommandSet
from libqtile.log_utils import init_log, logger


@pytest.fixture
def fake_qtile():
    class FakeQtile:
        def spawn(self, value):
            logger.warning(value)

    yield FakeQtile()


@pytest.fixture
def log_extension_output(monkeypatch):
    init_log()

    async def fake_async_subprocess(cmd, *args, **kwargs):
        class AsyncProc:
            async def communicate(self, value_in, *args):
                if value_in.startswith(b"missing"):
                    return [b"something_else", None]
                else:
                    return [value_in, None]

        return AsyncProc()

    monkeypatch.setattr(
        "libqtile.extension.base.asyncio.create_subprocess_exec", fake_async_subprocess
    )

    yield


@pytest.mark.usefixtures("log_extension_output")
def test_command_set_valid_command(caplog, fake_qtile):
    """Extension should run pre-commands and selected command."""

    async def t():
        extension = CommandSet(
            pre_commands=["run pre-command"], commandset={"key": "run testcommand"}
        )
        extension._configure(fake_qtile)
        extension.run()

        tries = 0

        while len(caplog.record_tuples) < 2 and tries < 5:
            await asyncio.sleep(0.1)
            tries += 1

        assert caplog.record_tuples == [
            ("libqtile", logging.WARNING, "run pre-command"),
            ("libqtile", logging.WARNING, "run testcommand"),
        ]

    asyncio.run(t())


@pytest.mark.usefixtures("log_extension_output")
def test_command_set_invalid_command(caplog, fake_qtile):
    """Where the key is not in "commands", no command will be run."""

    async def t():
        extension = CommandSet(
            pre_commands=["run pre-command"], commandset={"missing": "run testcommand"}
        )
        extension._configure(fake_qtile)
        extension.run()

        tries = 0

        while len(caplog.record_tuples) < 1 and tries < 5:
            await asyncio.sleep(0.1)
            tries += 1

        assert caplog.record_tuples == [("libqtile", logging.WARNING, "run pre-command")]

    asyncio.run(t())


@pytest.mark.usefixtures("log_extension_output")
def test_command_set_inside_command_set_valid_command(caplog, fake_qtile):
    """Extension should run pre-commands and selected command."""

    async def t():
        inside_command = CommandSet(
            pre_commands=["run inner pre-command"],
            commandset={"key": "run testcommand"},
        )
        inside_command._configure(fake_qtile)

        extension = CommandSet(
            pre_commands=["run pre-command"],
            commandset={"key": inside_command},
        )
        extension._configure(fake_qtile)
        extension.run()

        tries = 0

        while len(caplog.record_tuples) < 3 and tries < 5:
            await asyncio.sleep(0.1)
            tries += 1

        assert caplog.record_tuples == [
            ("libqtile", logging.WARNING, "run pre-command"),
            (
                "libqtile",
                logging.WARNING,
                "run inner pre-command",
            ),  # pre-command of the inside_command
            ("libqtile", logging.WARNING, "run testcommand"),
        ]

    asyncio.run(t())


@pytest.mark.usefixtures("log_extension_output")
def test_command_set_inside_command_set_invalid_command(caplog, fake_qtile):
    """Where the key is not in "commands", no command will be run."""

    async def t():
        inside_command = CommandSet(
            pre_commands=["run inner pre-command"],
            commandset={"key": "run testcommand"},  # doesn't really matter what command
        )
        inside_command._configure(fake_qtile)

        extension = CommandSet(
            pre_commands=["run pre-command"], commandset={"missing": inside_command}
        )
        extension._configure(fake_qtile)
        extension.run()

        tries = 0

        while len(caplog.record_tuples) < 1 and tries < 5:
            await asyncio.sleep(0.1)
            tries += 1

        assert caplog.record_tuples == [("libqtile", logging.WARNING, "run pre-command")]

        caplog.clear()

        inside_command = CommandSet(
            pre_commands=["run inner pre-command"],
            commandset={"missing": "run testcommand"},
        )
        inside_command._configure(fake_qtile)

        extension = CommandSet(
            pre_commands=["run pre-command"],
            commandset={"key": inside_command},
        )
        extension._configure(fake_qtile)
        extension.run()

        tries = 0

        while len(caplog.record_tuples) < 2 and tries < 5:
            await asyncio.sleep(0.1)
            tries += 1

        assert caplog.record_tuples == [
            ("libqtile", logging.WARNING, "run pre-command"),
            (
                "libqtile",
                logging.WARNING,
                "run inner pre-command",
            ),  # pre-command of the inside_command
        ]

    asyncio.run(t())
