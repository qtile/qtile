import hashlib
import os
import shutil
import subprocess
import tempfile
import textwrap

from libqtile.scripts.migrate import BACKUP_SUFFIX


def run_qtile_migrate(config):
    cmd = os.path.join(os.path.dirname(__file__), '..', 'bin', 'qtile')
    argv = [cmd, "migrate", "-c", config]
    subprocess.check_call(argv)


def hash_file(p):
    with open(p) as f:
        h = hashlib.sha256()
        h.update(f.read().encode('utf-8'))
        return h.digest()


def test_migrate_default_config_noop():
    with tempfile.TemporaryDirectory() as temp:
        default_config = os.path.join(os.path.dirname(__file__), '..', 'libqtile', 'resources', 'default_config.py')
        config_path = os.path.join(temp, "config.py")
        shutil.copyfile(default_config, config_path)
        run_qtile_migrate(config_path)

        original = hash_file(config_path)
        migrated = hash_file(config_path+BACKUP_SUFFIX)

        assert original == migrated


def read_file(p):
    with open(p) as f:
        return f.read()


def check_migrate(orig, expected):
    with tempfile.TemporaryDirectory() as tempdir:
        config_path = os.path.join(tempdir, "config.py")
        with open(config_path, "wb") as f:
            f.write(orig.encode('utf-8'))

        run_qtile_migrate(config_path)

        config_path = os.path.join(tempdir, "config.py")
        assert expected == read_file(config_path)
        assert orig == read_file(config_path+BACKUP_SUFFIX)


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


def test_libqtile_command_graph():
    orig = textwrap.dedent("""
        from libqtile.command_graph import CommandObject

        o = CommandObject()
    """)

    expected = textwrap.dedent("""
        from libqtile.command.graph import CommandObject

        o = CommandObject()
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
        from libqtile.widget import ThreadedPollText

        class MyWidget(ThreadedPollText):
            pass
    """)

    expected = textwrap.dedent("""
        from libqtile.widget import ThreadPoolText

        class MyWidget(ThreadPoolText):
            pass
    """)

    check_migrate(orig, expected)


def test_pacman():
    orig = textwrap.dedent("""
        from libqtile import bar
        from libqtile.widget import Pacman

        bar.Bar([Pacman()])
    """)

    expected = textwrap.dedent("""
        from libqtile import bar
        from libqtile.widget import CheckUpdates

        bar.Bar([CheckUpdates()])
    """)

    check_migrate(orig, expected)
