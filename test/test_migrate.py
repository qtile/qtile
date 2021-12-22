import hashlib
import os
import shutil
import subprocess
import tempfile
import textwrap

import pytest

from libqtile.scripts.migrate import BACKUP_SUFFIX
from test.test_check import have_mypy, run_qtile_check


def run_qtile_migrate(config):
    cmd = os.path.join(os.path.dirname(__file__), "..", "bin", "qtile")
    argv = [cmd, "migrate", "--yes", "-c", config]
    subprocess.check_call(argv)


def hash_file(p):
    with open(p) as f:
        h = hashlib.sha256()
        h.update(f.read().encode("utf-8"))
        return h.digest()


def test_migrate_default_config_noop():
    with tempfile.TemporaryDirectory() as temp:
        default_config = os.path.join(
            os.path.dirname(__file__), "..", "libqtile", "resources", "default_config.py"
        )
        config_path = os.path.join(temp, "config.py")
        shutil.copyfile(default_config, config_path)

        before = hash_file(config_path)
        run_qtile_migrate(config_path)
        after = hash_file(config_path)

        assert before == after
        assert not os.path.exists(config_path + BACKUP_SUFFIX)


def read_file(p):
    with open(p) as f:
        return f.read()


def test_extra_files_are_ok():
    with tempfile.TemporaryDirectory() as tempdir:
        config_file = os.path.join(tempdir, "config.py")
        with open(config_file, "w") as config:
            config.write("from .bar import CommandGraphRoot\n")
        bar_py = os.path.join(tempdir, "bar.py")
        with open(bar_py, "w") as config:
            config.write("from libqtile.command_graph import CommandGraphRoot\n")
        run_qtile_migrate(config_file)
        assert os.path.exists(bar_py + BACKUP_SUFFIX)
        assert read_file(bar_py) == "from libqtile.command.graph import CommandGraphRoot\n"


def check_migrate(orig, expected):
    with tempfile.TemporaryDirectory() as tempdir:
        config_path = os.path.join(tempdir, "config.py")
        with open(config_path, "wb") as f:
            f.write(orig.encode("utf-8"))

        run_qtile_migrate(config_path)
        if have_mypy():
            assert run_qtile_check(config_path)

        assert expected == read_file(config_path)
        assert orig == read_file(config_path + BACKUP_SUFFIX)


def test_window_name_change():
    orig = textwrap.dedent(
        """
        from libqtile import hook

        @hook.subscribe.window_name_change
        def f():
            pass
    """
    )

    expected = textwrap.dedent(
        """
        from libqtile import hook

        @hook.subscribe.client_name_updated
        def f():
            pass
    """
    )
    check_migrate(orig, expected)


def test_modules_renames():
    orig = textwrap.dedent(
        """
        from libqtile.command_graph import CommandGraphRoot
        from libqtile.command_client import CommandClient
        from libqtile.command_interface import CommandInterface
        from libqtile.command_object import CommandObject
        from libqtile.window import Internal

        print(
            CommandGraphRoot, CommandClient, CommandInterface, CommandObject, Internal
        )
    """
    )

    expected = textwrap.dedent(
        """
        from libqtile.command.graph import CommandGraphRoot
        from libqtile.command.client import CommandClient
        from libqtile.command.interface import CommandInterface
        from libqtile.command.base import CommandObject
        from libqtile.backend.x11.window import Internal

        print(
            CommandGraphRoot, CommandClient, CommandInterface, CommandObject, Internal
        )
    """
    )

    check_migrate(orig, expected)


def test_tile_master_windows():
    orig = textwrap.dedent(
        """
        from libqtile.layout import Tile

        t = Tile(masterWindows=2)
    """
    )

    expected = textwrap.dedent(
        """
        from libqtile.layout import Tile

        t = Tile(master_length=2)
    """
    )

    check_migrate(orig, expected)


def test_threaded_poll_text():
    orig = textwrap.dedent(
        """
        from libqtile.widget.base import ThreadedPollText

        class MyWidget(ThreadedPollText):
            pass
    """
    )

    expected = textwrap.dedent(
        """
        from libqtile.widget.base import ThreadPoolText

        class MyWidget(ThreadPoolText):
            pass
    """
    )

    check_migrate(orig, expected)


def test_pacman():
    orig = textwrap.dedent(
        """
        from libqtile import bar
        from libqtile.widget import Pacman

        bar.Bar([Pacman()], 30)
    """
    )

    expected = textwrap.dedent(
        """
        from libqtile import bar
        from libqtile.widget import CheckUpdates

        bar.Bar([CheckUpdates()], 30)
    """
    )

    check_migrate(orig, expected)


def test_crypto():
    orig = textwrap.dedent(
        """
        from libqtile import bar
        from libqtile.widget import BitcoinTicker

        bar.Bar(
            [
                BitcoinTicker(crypto='BTC', format='BTC: {avg}'),
                BitcoinTicker(format='{crypto}: {avg}', font='sans'),
                BitcoinTicker(),
                BitcoinTicker(currency='EUR', format='{avg}', foreground='ffffff'),
            ],
            30
        )
    """
    )

    expected = textwrap.dedent(
        """
        from libqtile import bar
        from libqtile.widget import CryptoTicker

        bar.Bar(
            [
                CryptoTicker(crypto='BTC'),
                CryptoTicker( font='sans'),
                CryptoTicker(),
                CryptoTicker(currency='EUR', foreground='ffffff'),
            ],
            30
        )
    """
    )

    check_migrate(orig, expected)


def test_main():
    orig = textwrap.dedent(
        """
        def main(qtile):
            qtile.do_something()
    """
    )

    expected = textwrap.dedent(
        """
        from libqtile import hook, qtile
        @hook.subscribe.startup
        def main():
            qtile.do_something()
    """
    )

    check_migrate(orig, expected)

    noop = textwrap.dedent(
        """
        from libqtile.hook import subscribe
        @subscribe.startup
        def main():
            pass
    """
    )
    with pytest.raises(FileNotFoundError):
        check_migrate(noop, noop)


def test_new_at_current_to_new_client_position():
    orig = textwrap.dedent(
        """
        from libqtile import layout

        layouts = [
            layout.MonadTall(border_focus='#ff0000', new_at_current=False),
            layout.MonadWide(new_at_current=True, border_focus='#ff0000'),
        ]
    """
    )

    expected = textwrap.dedent(
        """
        from libqtile import layout

        layouts = [
            layout.MonadTall(border_focus='#ff0000', new_client_position='after_current'),
            layout.MonadWide(new_client_position='before_current', border_focus='#ff0000'),
        ]
    """
    )

    check_migrate(orig, expected)


def test_windowtogroup_groupName_argument():  # noqa: N802
    orig = textwrap.dedent(
        """
        from libqtile.config import Key
        from libqtile.lazy import lazy

        k = Key([], 's', lazy.window.togroup(groupName="g"))
        c = lambda win: win.cmd_togroup(groupName="g")
    """
    )

    expected = textwrap.dedent(
        """
        from libqtile.config import Key
        from libqtile.lazy import lazy

        k = Key([], 's', lazy.window.togroup(group_name="g"))
        c = lambda win: win.cmd_togroup(group_name="g")
    """
    )

    check_migrate(orig, expected)
