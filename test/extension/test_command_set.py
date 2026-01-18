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


@pytest.mark.usefixtures("log_extension_output")
def test_command_set_inside_command_set_valid_command(caplog, fake_qtile):
    """Extension should run pre-commands and selected command."""

    inside_command = CommandSet(
        pre_commands=["run inner pre-command"],
        commands={"key": "run testcommand"},
    )
    inside_command._configure(fake_qtile)

    extension = CommandSet(
        pre_commands=["run pre-command"],
        commands={"key": inside_command},
    )
    extension._configure(fake_qtile)

    extension.run()

    assert caplog.record_tuples == [
        ("libqtile", logging.WARNING, "run pre-command"),
        (
            "libqtile",
            logging.WARNING,
            "run inner pre-command",
        ),  # pre-command of the inside_command
        ("libqtile", logging.WARNING, "run testcommand"),
    ]


@pytest.mark.usefixtures("log_extension_output")
def test_command_set_inside_command_set_invalid_command(caplog, fake_qtile):
    """Where the key is not in "commands", no command will be run."""
    inside_command = CommandSet(
        pre_commands=["run inner pre-command"],
        commands={"key": "run testcommand"},  # doesn't really matter what command
    )
    inside_command._configure(fake_qtile)

    extension = CommandSet(pre_commands=["run pre-command"], commands={"missing": inside_command})
    extension._configure(fake_qtile)
    extension.run()

    assert caplog.record_tuples == [("libqtile", logging.WARNING, "run pre-command")]

    caplog.clear()

    inside_command = CommandSet(
        pre_commands=["run inner pre-command"],
        commands={"missing": "run testcommand"},
    )
    inside_command._configure(fake_qtile)

    extension = CommandSet(
        pre_commands=["run pre-command"],
        commands={"key": inside_command},
    )
    extension._configure(fake_qtile)

    extension.run()

    assert caplog.record_tuples == [
        ("libqtile", logging.WARNING, "run pre-command"),
        (
            "libqtile",
            logging.WARNING,
            "run inner pre-command",
        ),  # pre-command of the inside_command
    ]
