# Copyright (c) 2020, Tycho Andersen. All rights reserved.
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
# SOFTWARE.

# Set the locale before any widgets or anything are imported, so any widget
# whose defaults depend on a reasonable locale sees something reasonable.
import shutil
import subprocess
import sys
from os import getenv, path

from libqtile import confreader


def check_config(args):
    print("checking qtile config file {}".format(args.configfile))

    # does the config type check?
    if shutil.which("mypy") is None:
        print("mypy not found, can't type check config file\n"
              "install it and try again")
    else:
        try:
            subprocess.check_call(["mypy", args.configfile])
            print("config file type checking succeeded")
        except subprocess.CalledProcessError as e:
            print("config file type checking failed: {}".format(e))
            sys.exit(1)

    # can we load the config?
    config = confreader.Config(args.configfile)
    config.load()
    config.validate()
    print("config file can be loaded by qtile")


def add_subcommand(subparsers):
    parser = subparsers.add_parser("check", help="Check a configuration file for errors")
    parser.add_argument(
        "-c", "--config",
        action="store",
        default=path.expanduser(path.join(
            getenv('XDG_CONFIG_HOME', '~/.config'), 'qtile', 'config.py')),
        dest="configfile",
        help='Use the specified configuration file',
    )
    parser.set_defaults(func=check_config)
