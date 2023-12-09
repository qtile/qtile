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
from __future__ import annotations

import argparse
import os
import os.path
import shutil
import sys
from glob import glob
from pathlib import Path
from typing import TYPE_CHECKING

from libqtile.scripts.migrations import MIGRATIONS, load_migrations
from libqtile.utils import get_config_file

if TYPE_CHECKING:
    from typing import Iterator

BACKUP_SUFFIX = ".migrate.bak"


try:
    import libcst
except ImportError:
    pass


class AbortMigration(Exception):
    pass


class SkipFile(Exception):
    pass


def version_tuple(value: str) -> tuple[int, ...]:
    try:
        val = tuple(int(x) for x in value.split("."))
        return val
    except TypeError:
        raise argparse.ArgumentTypeError("Cannot parse version string.")


def file_and_backup(config_dir: str) -> Iterator[tuple[str, str]]:
    if os.path.isfile(config_dir):
        config_dir = os.path.dirname(config_dir)
    for py in glob(os.path.join(config_dir, "*.py")):
        backup = py + BACKUP_SUFFIX
        yield py, backup


class QtileMigrate:
    """
    May be overkill to use a class here but we can store state (i.e. args)
    without needing to pass them around all the time.
    """

    def __call__(self, args: argparse.Namespace) -> None:
        """
        This is called by ArgParse when we run `qtile migrate`. The parsed options are
        passed as an argument.
        """
        if "libcst" not in sys.modules:
            print("libcst can't be found. Unable to migrate config file.")
            print("Please install it and try again.")
            sys.exit(1)

        self.args = args
        self.filter_migrations()

        if self.args.list_migrations:
            self.list_migrations()
            return
        elif self.args.info:
            self.show_migration_info()
            return
        else:
            self.run_migrations()

    def filter_migrations(self) -> None:
        load_migrations()
        if self.args.run_migrations:
            self.migrations = [m for m in MIGRATIONS if m.ID in self.args.run_migrations]
        elif self.args.after_version:
            self.migrations = [m for m in MIGRATIONS if m.get_version() > self.args.after_version]
        else:
            self.migrations = MIGRATIONS

        if not self.migrations:
            sys.exit("No migrations found.")

    def list_migrations(self) -> None:
        width = max(len(m.ID) for m in self.migrations) + 4

        ordered = sorted(self.migrations, key=lambda m: (m.get_version(), m.ID))

        print(f"ID{' ' * (width - 2)}{'After Version':<15}Summary")
        for m in ordered:
            summary = m.show_summary().replace("``", "'")
            print(f"{m.ID:<{width}}{m.AFTER_VERSION:^15}{summary}")

    def show_migration_info(self) -> None:
        migration_id = self.args.info
        migration = [m for m in MIGRATIONS if m.ID == migration_id]
        if not migration:
            print(f"Unknown migration: {migration_id}")
            sys.exit(1)

        print(f"{migration_id}:")
        print(migration[0].show_help())

    def get_source(self, path: str) -> libcst.metadata.MetadataWrapper:
        module = libcst.parse_module(Path(path).read_text())
        return libcst.metadata.MetadataWrapper(module)

    def lint(self, path: str) -> None:
        print(f"{path}:")
        source = self.get_source(path)
        lint_lines = []

        for m in self.migrations:
            migrator = m()
            migrator.migrate(source)
            lint_lines.extend(migrator.show_lint())

        lint_lines.sort()
        print("\n".join(map(str, lint_lines)))

    def migrate(self, path: str) -> bool:
        source: libcst.metadata.MetadataWrapper | libcst.Module = self.get_source(path)
        changed = False

        for m in self.migrations:
            migrator = m()
            migrator.migrate(source)

            diff = migrator.show_diff(self.args.no_colour)

            if diff:
                if self.args.show_diff or not self.args.yes:
                    print(f"{m.ID}: {m.show_summary()}\n")
                    print(f"{diff}\n")

                if self.args.yes:
                    assert migrator.updated is not None
                    source = libcst.metadata.MetadataWrapper(migrator.updated)
                    changed = True

                else:
                    while (
                        a := input("Apply changes? (y)es, (n)o, (s)kip file, (q)uit. ").lower()
                    ) not in ("y", "n", "s", "q"):
                        print("Unexpected response. Try again.")

                    if a == "y":
                        assert migrator.updated is not None
                        source = libcst.metadata.MetadataWrapper(migrator.updated)
                        changed = True
                    elif a == "n":
                        assert migrator.original is not None
                        source = migrator.original
                    elif a == "s":
                        raise SkipFile
                    elif a == "q":
                        raise AbortMigration

        if not changed:
            return False

        if not self.args.yes:
            while (save := input(f"Save all changes to {path}? (y)es, (n)o. ").lower()) not in (
                "y",
                "n",
            ):
                print("Unexpected response. Try again.")
            do_save = save == "y"
        else:
            do_save = True

        if do_save:
            if isinstance(source, libcst.metadata.MetadataWrapper):
                source = source.module
            Path(f"{path}").write_text(source.code)
            print("Saved!")
            return True
        else:
            return False

    def run_migrations(self) -> None:
        backups = []
        changed_files = []
        aborted = False

        for py, backup in file_and_backup(self.args.config):
            if self.args.lint:
                self.lint(py)
                continue
            else:
                try:
                    shutil.copyfile(py, backup)
                    backups.append(backup)
                    changed = self.migrate(py)
                    if changed:
                        changed_files.append(py)
                except SkipFile:
                    backups.remove(backup)
                    continue
                except AbortMigration:
                    aborted = True
                    break

        if aborted:
            print("Migration aborted. Reverting changes.")
            for f in changed_files:
                shutil.copyfile(f + BACKUP_SUFFIX, f)

        elif backups:
            print("Finished. Backup files have not been deleted.")


def add_subcommand(subparsers, parents):
    parser = subparsers.add_parser(
        "migrate", parents=parents, help="Migrate a configuration file to the current API."
    )
    parser.add_argument(
        "-c",
        "--config",
        action="store",
        default=get_config_file(),
        help="Use the specified configuration file (migrates every .py file in this directory).",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Automatically apply diffs with no confirmation.",
    )
    parser.add_argument(
        "--show-diff", action="store_true", help="When used with --yes, will still output diff."
    )
    parser.add_argument(
        "--lint", action="store_true", help="Providing linting output but don't update config."
    )
    parser.add_argument(
        "--list-migrations", action="store_true", help="List available migrations."
    )
    parser.add_argument(
        "--info",
        metavar="ID",
        help="Show detailed info for the migration with the given ID",
    )
    parser.add_argument(
        "--after-version",
        metavar="VERSION",
        type=version_tuple,
        help="Run migrations introduced after VERSION.",
    )
    parser.add_argument(
        "-r",
        "--run-migrations",
        type=lambda value: value.split(","),
        metavar="ID",
        help="Run named migration[s]. Comma separated list for multiple migrations",
    )
    parser.add_argument(
        "--no-colour", action="store_true", help="Do not use colour in diff output."
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Increase output verbosity")
    parser.set_defaults(func=QtileMigrate())
