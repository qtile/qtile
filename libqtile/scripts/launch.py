"""
Command-line wrapper to launch process from within qtile
"""

import argparse
import os


def launch(opts) -> None:
    fd = opts.fd

    if fd > 0:
        # Open the file descriptor
        with open(fd, "rb+", 0) as sock:
            # Tell qtile we're ready to listen for their message
            sock.write(b"READY")

            # Receive OK message (but we're not checking the contents, we just
            # block until we receive the data)
            _ = sock.read(2)

        # Tidy up. Close any file descriptors other than stdin, stdout and stderr
        os.closerange(3, -1)

    # Launch the process
    os.execvp(opts.cmd, [opts.cmd] + opts.args)


def add_subcommand(subparsers, parents):
    parser = subparsers.add_parser(
        "launch", parents=parents, help="Launch process from within qtile."
    )
    parser.add_argument(
        "--fd", type=int, default=-1, help="Wait for message on IPC before launching process."
    )
    parser.add_argument("cmd", help="Command to execute.")
    parser.add_argument(
        "args",
        nargs=argparse.REMAINDER,
        metavar="[args ...]",
        help="Optional arguments to pass to command.",
    )
    parser.set_defaults(func=launch)
