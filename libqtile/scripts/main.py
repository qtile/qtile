import argparse
import logging
import sys

from libqtile.log_utils import init_log
from libqtile.scripts import check, cmd_obj, migrate, run_cmd, shell, start, top

try:
    # Python>3.7 can get the version from importlib
    from importlib.metadata import distribution

    VERSION = distribution("qtile").version
except ModuleNotFoundError:
    try:
        # pkg_resources is required for 3.7
        import pkg_resources

        VERSION = pkg_resources.require("qtile")[0].version
    except (pkg_resources.DistributionNotFound, ModuleNotFoundError):
        VERSION = "dev"


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

    main_parser = argparse.ArgumentParser(
        prog="qtile",
        description="A full-featured, pure-Python tiling window manager.",
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

    # `qtile help` should print help
    def print_help(options):
        main_parser.print_help()

    help_ = subparsers.add_parser("help", help="Print help information and exit")
    help_.set_defaults(func=print_help)

    options = main_parser.parse_args()
    try:
        log_level = getattr(logging, options.log_level)
        init_log(log_level=log_level, log_color=sys.stdout.isatty())
        options.func(options)
    except AttributeError:
        main_parser.print_usage()
        print("")
        print("Did you mean:")
        print(" ".join(sys.argv + ["start"]))
        sys.exit(1)


if __name__ == "__main__":
    main()
