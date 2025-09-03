import argparse
import logging
import sys
from pathlib import Path

from libqtile.log_utils import get_default_log, init_log
from libqtile.scripts import (
    check,
    cmd_obj,
    launch,
    migrate,
    repl,
    run_cmd,
    shell,
    start,
    top,
)
from libqtile.utils import VERSION


def main():
    parent_parser = argparse.ArgumentParser(add_help=False)
    parent_parser.add_argument(
        "-l",
        "--log-level",
        default="WARNING",
        dest="log_level",
        type=str.upper,
        choices=("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"),
        help="Set qtile log level",
    )
    parent_parser.add_argument(
        "-p",
        "--log-path",
        default=get_default_log(),
        dest="log_path",
        type=Path,
        help="Set alternative qtile log path",
    )
    main_parser = argparse.ArgumentParser(
        prog="qtile",
        description="A full-featured tiling window manager for X11 and Wayland.",
    )
    main_parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=VERSION,
    )

    subparsers = main_parser.add_subparsers()
    start.add_subcommand(subparsers, [parent_parser])
    shell.add_subcommand(subparsers, [parent_parser])
    top.add_subcommand(subparsers, [parent_parser])
    run_cmd.add_subcommand(subparsers, [parent_parser])
    cmd_obj.add_subcommand(subparsers, [parent_parser])
    check.add_subcommand(subparsers, [parent_parser])
    migrate.add_subcommand(subparsers, [parent_parser])
    launch.add_subcommand(subparsers, [parent_parser])
    repl.add_subcommand(subparsers, [parent_parser])

    # `qtile help` should print help
    def print_help(options):
        main_parser.print_help()

    help_ = subparsers.add_parser(
        "help", help="Print help message and exit.", parents=[parent_parser]
    )
    help_.set_defaults(func=print_help)

    options = main_parser.parse_args()
    if func := getattr(options, "func", None):
        log_level = getattr(logging, options.log_level)
        init_log(log_level, log_path=options.log_path)
        func(options)
    else:
        main_parser.print_usage()
        print("")
        print("Did you mean:")
        print(" ".join(sys.argv + ["start"]))
        sys.exit(1)


if __name__ == "__main__":
    main()
