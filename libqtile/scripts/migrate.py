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
import shutil
import sys

BACKUP_SUFFIX = ".migrate.bak"

try:
    import bowler
except ImportError:
    pass


def rename_hook(config, fro, to):
    # could match on dotted_name< 'hook' '.' 'subscribe' '.' '{name}' >
    # but the replacement gets more complicated...
    selector = "'{name}'".format(name=fro)
    q = bowler.Query(config).select_pattern(selector)
    q.current.kwargs["name"] = fro
    return q.rename(to)


def client_name_updated(config):
    """ Rename window_name_change -> client_name_updated"""
    return rename_hook(config, "window_name_change", "client_name_updated")


def tile_master_windows_rename(config):
    return (
        bowler.Query(config)
        .select_function("Tile")
        .modify_argument("masterWindows", "master_length")
    )


def threaded_poll_text_rename(config):
    return (
        bowler.Query(config)
        .select_class("ThreadedPollText")
        .rename("ThreadPoolText")
    )


def pacman_to_checkupdates(config):
    return (
        bowler.Query(config)
        .select_class("Pacman")
        .rename("CheckUpdates")
    )


def hook_main_function(config):
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
        bowler.Query(config)
        .select_function("main")
        .is_def()
        .modify(modify_main)
    )


MIGRATIONS = [
    client_name_updated,
    tile_master_windows_rename,
    threaded_poll_text_rename,
    pacman_to_checkupdates,
    hook_main_function,
]


MODULE_RENAMES = [
    ("libqtile.command_graph", "libqtile.command.graph"),
    ("libqtile.command_client", "libqtile.command.client"),
    ("libqtile.command_interface", "libqtile.command.interface"),
    ("libqtile.command_object", "libqtile.command.object"),
]

for (fro, to) in MODULE_RENAMES:
    def f(config, fro=fro, to=to):
        return (
            bowler.Query(config)
            .select_module(fro)
            .rename(to)
        )
    MIGRATIONS.append(f)


def do_migrate(args):
    if "bowler" not in sys.modules:
        print("bowler can't be found, not migrating config file")
        print("install it and try again")
        sys.exit(1)

    backup = args.config + BACKUP_SUFFIX
    shutil.copyfile(args.config, backup)

    for m in MIGRATIONS:
        m(args.config).execute(interactive=args.interactive, write=True)

    if filecmp.cmp(args.config, backup, shallow=False):
        print("Config unchanged.")
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
        help="Use the specified configuration file",
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Interactively apply diff (similar to git add -p)",
    )
    parser.set_defaults(func=do_migrate)
