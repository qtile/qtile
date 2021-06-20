# Copyright (c) 2021, Tycho Andersen. All rights reserved.
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
import filecmp
import os
import os.path
import re
import shutil
import sys
from glob import glob

BACKUP_SUFFIX = ".migrate.bak"

try:
    import bowler
except ImportError:
    pass


def rename_hook(query, fro, to):
    # could match on dotted_name< 'hook' '.' 'subscribe' '.' '{name}' >
    # but the replacement gets more complicated...
    selector = "'{name}'".format(name=fro)
    q = query.select_pattern(selector)
    q.current.kwargs["name"] = fro
    return q.rename(to)


def client_name_updated(query):
    """ Rename window_name_change -> client_name_updated"""
    return rename_hook(query, "window_name_change", "client_name_updated")


def tile_master_windows_rename(query):
    return (
        query
        .select_function("Tile")
        .modify_argument("masterWindows", "master_length")
    )


def threaded_poll_text_rename(query):
    return (
        query
        .select_class("ThreadedPollText")
        .rename("ThreadPoolText")
    )


def pacman_to_checkupdates(query):
    return (
        query
        .select_class("Pacman")
        .rename("CheckUpdates")
    )


def hook_main_function(query):
    def modify_main(node, capture, filename):
        main = capture.get("function_def")
        if main.prev_sibling:
            for leaf in main.prev_sibling.leaves():
                if "startup" == leaf.value:
                    return
        args = capture.get("function_arguments")
        if args:
            args[0].remove()
            main.prefix += "from libqtile import hook, qtile\n"
            main.prefix += "@hook.subscribe.startup\n"

    return (
        query
        .select_function("main")
        .is_def()
        .modify(modify_main)
    )


# Deprecated new_at_current key replaced by new_client_position.
# In the node, we want to change the key name
# and adapts its value depending of the previous value :
#   new_at_current=True => new_client_position=before_current
#   new_at_current<>True => new_client_position=after_current
def update_node_nac(node, capture, filename):
    key = capture.get("k")
    key.value = "new_client_position"
    val = capture.get("v")
    if val.value == "True":
        val.value = "'before_current'"
    else:
        val.value = "'after_current'"


def new_at_current_to_new_client_position(query):
    old_pattern = """
        argument< k="new_at_current" "=" v=any >
    """
    return (
        query
        .select(old_pattern)
        .modify(update_node_nac)
    )


MIGRATIONS = [
    # from 0.17.0
    client_name_updated,
    tile_master_windows_rename,
    threaded_poll_text_rename,
    pacman_to_checkupdates,
    hook_main_function,
    new_at_current_to_new_client_position,
]


MODULE_RENAMES = [
    # from 0.17.0
    ("libqtile.command_graph", "libqtile.command.graph"),
    ("libqtile.command_client", "libqtile.command.client"),
    ("libqtile.command_interface", "libqtile.command.interface"),
    ("libqtile.command_object", "libqtile.command.base"),
    ("libqtile.window", "libqtile.backend.x11.window"),
]

for (fro, to) in MODULE_RENAMES:
    def f(query, fro=fro, to=to):
        return (
            query
            .select_module(fro)
            .rename(to)
        )
    MIGRATIONS.append(f)


# Number of migrations that have been removed.
PREVIOUS_MIGRATIONS = 0

MIGRATION_COUNT_PATTERN = re.compile(r"^migration_count\s*=\s*(\d+)\s*")


def get_migration_count(config):
    # this is fairly horrible, but there's no guarantee we can __import__() a
    # config file in the current version, since it may not have been migrated
    # yet. so we parse it manually :)
    with open(config) as f:
        for line in f.readlines():
            match = MIGRATION_COUNT_PATTERN.fullmatch(line)
            if match is not None:
                return int(match.group(1))

    # didn't find it, so the file hasn't been migrated before
    return 0


def set_migration_count(config):
    new_migration_count = "migration_count = {}".format(PREVIOUS_MIGRATIONS + len(MIGRATIONS))
    written = False
    with open(config, "r+") as f:
        lines = f.readlines()
        f.seek(0)
        for line in lines:
            match = MIGRATION_COUNT_PATTERN.fullmatch(line)
            if match is not None:
                written = True
                f.write(new_migration_count)
                f.write("\n")
            else:
                f.write(line)

    if not written:
        with open(config, "a") as f:
            f.write(new_migration_count)
            f.write("\n")


def file_and_backup(config_dir):
    for py in glob(os.path.join(config_dir, "*.py")):
        backup = py + BACKUP_SUFFIX
        yield py, backup


def do_migrate(args):
    if "bowler" not in sys.modules:
        print("bowler can't be found, not migrating config file")
        print("install it and try again")
        sys.exit(1)

    migration_count = get_migration_count(args.config)

    config_dir = os.path.dirname(args.config)
    for py, backup in file_and_backup(config_dir):
        shutil.copyfile(py, backup)

    # we only want to do migrations that haven't been done before
    needed_migrations = MIGRATIONS[migration_count-PREVIOUS_MIGRATIONS:]
    for m in needed_migrations:
        q = bowler.Query(config_dir)
        m(q).execute(interactive=args.interactive, write=True)

    # if we actually did some migrations, let's update the migration_count
    if len(needed_migrations) > 0:
        set_migration_count(args.config)

    changed = False
    for py, backup in file_and_backup(config_dir):
        backup = py + BACKUP_SUFFIX
        if not filecmp.cmp(py, backup, shallow=False):
            changed = True
            break

    if not changed:
        print("Config unchanged.")
        for _, backup in file_and_backup(config_dir):
            os.remove(backup)


def add_subcommand(subparsers, parents):
    parser = subparsers.add_parser(
        "migrate",
        parents=parents,
        help="Migrate a configuration file to the current API"
    )
    parser.add_argument(
        "-c",
        "--config",
        action="store",
        default=os.path.expanduser(
            os.path.join(os.getenv("XDG_CONFIG_HOME", "~/.config"), "qtile", "config.py")
        ),
        help="Use the specified configuration file (migrates every .py file in this directory)",
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Interactively apply diff (similar to git add -p)",
    )
    parser.set_defaults(func=do_migrate)
