import argparse
import logging
import sys

from libqtile.log_utils import init_log
from libqtile.scripts import check, cmd_obj, migrate, run_cmd, shell, start, top

try:
    import pkg_resources
    VERSION = pkg_resources.require("qtile")[0].version
except (pkg_resources.DistributionNotFound, ImportError):
    VERSION = 'dev'


def main():
    parent_parser = argparse.ArgumentParser(add_help=False)
    parent_parser.add_argument(
        '-l', '--log-level',
        default='WARNING',
        dest='log_level',
        type=str.upper,
        choices=('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'),
        help='Set qtile log level'
    )

    # TODO: remove the parents=[parent_parser], line when we remove the
    # backward compatibility hack below
    main_parser = argparse.ArgumentParser(
        prog='qtile',
        parents=[parent_parser],
        description='A full-featured, pure-Python tiling window manager.',
    )
    main_parser.add_argument(
        '--version',
        action='version',
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

    # `qtile help` should print help
    def print_help(options):
        main_parser.print_help()
    help_ = subparsers.add_parser("help", help="Print help information and exit")
    help_.set_defaults(func=print_help)

    options = main_parser.parse_args()
    log_level = getattr(logging, options.log_level)
    init_log(log_level=log_level, log_color=sys.stdout.isatty())

    # backward compat hack: `qtile` with no args (or non-subcommand args)
    # should default to `qtile start`. it seems impolite for commands to do
    # nothing when run with no args, so let's warn about this being deprecated.
    try:
        options.func(options)
    except AttributeError:
        print("please move to `qtile start` as your qtile invocation, "
              "instead of just `qtile`; this default will be removed Soon(TM)")
        start.start(options)
