import io
import os
import shutil
import subprocess
import tempfile
import textwrap

import pytest

from libqtile.scripts.migrate import (
    BACKUP_SUFFIX,
    MIGRATION_COUNT_PATTERN,
    MIGRATIONS,
    PREVIOUS_MIGRATIONS,
    rename_hook,
    set_migration_count,
)
from test.test_check import have_mypy, run_qtile_check


def run_qtile_migrate(config):
    cmd = os.path.join(os.path.dirname(__file__), '..', 'bin', 'qtile')
    argv = [cmd, "migrate", "-c", config]
    subprocess.check_call(argv)


def test_migrate_default_config_noop():
    with tempfile.TemporaryDirectory() as temp:
        default_config = os.path.join(os.path.dirname(__file__), '..', 'libqtile', 'resources', 'default_config.py')
        config_path = os.path.join(temp, "config.py")
        shutil.copyfile(default_config, config_path)
        set_migration_count(config_path)

        before = read_file_drop_migration_count(config_path)
        run_qtile_migrate(config_path)
        after = read_file_drop_migration_count(config_path)

        assert before == after
        assert not os.path.exists(config_path + BACKUP_SUFFIX)


def read_file_drop_migration_count(p):
    with open(p) as f:
        out = io.StringIO()
        for line in f.readlines():
            if MIGRATION_COUNT_PATTERN.fullmatch(line) is None:
                out.write(line)
        return out.getvalue()


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
        assert read_file_drop_migration_count(bar_py) == "from libqtile.command.graph import CommandGraphRoot\n"


def check_migrate(orig, expected, orig_has_migrate_count=False, expected_has_migrate_count=False):
    with tempfile.TemporaryDirectory() as tempdir:
        config_path = os.path.join(tempdir, "config.py")
        with open(config_path, "wb") as f:
            f.write(orig.encode('utf-8'))

        run_qtile_migrate(config_path)
        if have_mypy():
            assert run_qtile_check(config_path)

        if expected_has_migrate_count:
            with open(config_path) as f:
                assert expected == f.read()
        else:
            assert expected == read_file_drop_migration_count(config_path)
        if orig_has_migrate_count:
            with open(config_path+BACKUP_SUFFIX) as f:
                assert orig == f.read()
        else:
            assert orig == read_file_drop_migration_count(config_path+BACKUP_SUFFIX)


def test_migration_count_pattern():
    assert MIGRATION_COUNT_PATTERN.fullmatch("foo = 34\n") is None
    assert MIGRATION_COUNT_PATTERN.fullmatch("migration_count = 34") is not None
    assert MIGRATION_COUNT_PATTERN.fullmatch("migration_count = 34\n") is not None
    assert MIGRATION_COUNT_PATTERN.fullmatch("migration_count=34") is not None


def test_window_name_change():
    orig = textwrap.dedent("""
        from libqtile import hook

        @hook.subscribe.window_name_change
        def f():
            pass
    """)

    expected = textwrap.dedent("""
        from libqtile import hook

        @hook.subscribe.client_name_updated
        def f():
            pass
    """)
    check_migrate(orig, expected)


def test_modules_renames():
    orig = textwrap.dedent("""
        from libqtile.command_graph import CommandGraphRoot
        from libqtile.command_client import CommandClient
        from libqtile.command_interface import CommandInterface
        from libqtile.command_object import CommandObject
        from libqtile.window import Internal

        print(
            CommandGraphRoot, CommandClient, CommandInterface, CommandObject, Internal
        )
    """)

    expected = textwrap.dedent("""
        from libqtile.command.graph import CommandGraphRoot
        from libqtile.command.client import CommandClient
        from libqtile.command.interface import CommandInterface
        from libqtile.command.base import CommandObject
        from libqtile.backend.x11.window import Internal

        print(
            CommandGraphRoot, CommandClient, CommandInterface, CommandObject, Internal
        )
    """)

    check_migrate(orig, expected)


def test_tile_master_windows():
    orig = textwrap.dedent("""
        from libqtile.layout import Tile

        t = Tile(masterWindows=2)
    """)

    expected = textwrap.dedent("""
        from libqtile.layout import Tile

        t = Tile(master_length=2)
    """)

    check_migrate(orig, expected)


def test_threaded_poll_text():
    orig = textwrap.dedent("""
        from libqtile.widget.base import ThreadedPollText

        class MyWidget(ThreadedPollText):
            pass
    """)

    expected = textwrap.dedent("""
        from libqtile.widget.base import ThreadPoolText

        class MyWidget(ThreadPoolText):
            pass
    """)

    check_migrate(orig, expected)


def test_pacman():
    orig = textwrap.dedent("""
        from libqtile import bar
        from libqtile.widget import Pacman

        bar.Bar([Pacman()], 30)
    """)

    expected = textwrap.dedent("""
        from libqtile import bar
        from libqtile.widget import CheckUpdates

        bar.Bar([CheckUpdates()], 30)
    """)

    check_migrate(orig, expected)


def test_main():
    orig = textwrap.dedent("""
        def main(qtile):
            qtile.do_something()
    """)

    expected = textwrap.dedent("""
        from libqtile import hook, qtile
        @hook.subscribe.startup
        def main():
            qtile.do_something()
    """)

    check_migrate(orig, expected)

    noop = textwrap.dedent("""
        from libqtile.hook import subscribe
        @subscribe.startup
        def main():
            pass
        migration_count = {}
    """.format(len(MIGRATIONS)+PREVIOUS_MIGRATIONS))
    with pytest.raises(FileNotFoundError):
        check_migrate(noop, noop, expected_has_migrate_count=True)


def test_new_at_current_to_new_client_position():
    orig = textwrap.dedent("""
        from libqtile import layout

        layouts = [
            layout.MonadTall(border_focus='#ff0000', new_at_current=False),
            layout.MonadWide(new_at_current=True, border_focus='#ff0000'),
        ]
    """)

    expected = textwrap.dedent("""
        from libqtile import layout

        layouts = [
            layout.MonadTall(border_focus='#ff0000', new_client_position='after_current'),
            layout.MonadWide(new_client_position='before_current', border_focus='#ff0000'),
        ]
    """)

    check_migrate(orig, expected)


def fake_migration(query):
    rename_hook(query, "foo", "bar")


def test_migrate_count_correctly_skips():
    orig = textwrap.dedent("""
        foo = 43
    """)

    MIGRATIONS.append(fake_migration)
    check_migrate(orig, orig)
    MIGRATIONS.remove(fake_migration)


def test_migrate_count_adds_count():
    orig = textwrap.dedent("""
        from libqtile.config import Match
    """)

    expected = textwrap.dedent("""
        from libqtile.config import Match
        migration_count = {}
    """.format(len(MIGRATIONS)+PREVIOUS_MIGRATIONS))

    check_migrate(orig, expected, expected_has_migrate_count=True)


def test_migrate_count_sets_count():
    orig = textwrap.dedent("""
        from libqtile.config import Match

        migration_count = 0
    """)

    expected = textwrap.dedent("""
        from libqtile.config import Match

        migration_count = {}
    """.format(len(MIGRATIONS)+PREVIOUS_MIGRATIONS))

    check_migrate(orig, expected, orig_has_migrate_count=True, expected_has_migrate_count=True)
