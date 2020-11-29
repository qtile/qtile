import argparse
import logging
import sys

from libqtile.log_utils import init_log
from libqtile.scripts import check, cmd_obj, run_cmd, shell, start, top

try:
    import pkg_resources
    VERSION = pkg_resources.require("qtile")[0].version
except (pkg_resources.DistributionNotFound, ImportError):
    VERSION = 'dev'


def main():
    # backward compat hack: `qtile` with no args (or non-subcommand args)
    # should default to `qtile start`. it seems impolite for commands to do
    # nothing when run with no args, so let's warn about this being deprecated.
    if len(sys.argv) == 1:
        print("please move to `qtile start` as your qtile invocation, "
              "instead of just `qtile`; this default will be removed Soon(TM)")
        sys.argv.insert(1, "start")

    parser = argparse.ArgumentParser(
        prog='qtile',
        description='A full-featured, pure-Python tiling window manager.',
    )
    parser.add_argument(
        '--version',
        action='version',
        version=VERSION,
    )
    parser.add_argument(
        '-l', '--log-level',
        default='WARNING',
        dest='log_level',
        type=str.upper,
        choices=('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'),
        help='Set qtile log level'
    )

    subparsers = parser.add_subparsers()
    start.add_subcommand(subparsers)
    shell.add_subcommand(subparsers)
    top.add_subcommand(subparsers)
    run_cmd.add_subcommand(subparsers)
    cmd_obj.add_subcommand(subparsers)
    check.add_subcommand(subparsers)

    # `qtile help` should print help
    def print_help(options):
        parser.print_help()
    help_ = subparsers.add_parser("help", help="Print help information and exit")
    help_.set_defaults(func=print_help)

    options = parser.parse_args()
    log_level = getattr(logging, options.log_level)
    init_log(log_level=log_level, log_color=sys.stdout.isatty())
    options.func(options)
