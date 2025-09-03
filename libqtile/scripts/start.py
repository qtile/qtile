# Copyright (c) 2008, Aldo Cortesi. All rights reserved.
# Copyright (c) 2011, Florian Mounier
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
from __future__ import annotations

import locale
from os import makedirs, path
from pathlib import Path
from sys import exit
from typing import TYPE_CHECKING

import libqtile.backend
from libqtile import confreader, qtile
from libqtile.log_utils import logger
from libqtile.utils import VERSION, get_config_file

if TYPE_CHECKING:
    from libqtile.core.manager import Qtile


def rename_process():
    """
    Try to rename the qtile process if py-setproctitle is installed:

    http://code.google.com/p/py-setproctitle/

    Will fail silently if it's not installed. Setting the title lets you do
    stuff like "killall qtile".
    """
    try:
        import setproctitle

        setproctitle.setproctitle("qtile")
    except ImportError:
        pass


def make_qtile(options) -> Qtile | None:
    qtile.core.name = options.backend
    if missing_deps := libqtile.backend.has_deps(options.backend):
        print(f"Backend '{options.backend}' missing required Python dependencies:")
        for dep in missing_deps:
            print("\t", dep)

        return None

    kore = libqtile.backend.get_core(options.backend)

    if not path.isfile(options.configfile):
        try:
            makedirs(path.dirname(options.configfile), exist_ok=True)
            from shutil import copyfile

            default_config_path = path.join(
                path.dirname(__file__), "..", "resources", "default_config.py"
            )
            copyfile(default_config_path, options.configfile)
            logger.info("Copied default_config.py to %s", options.configfile)
        except Exception:
            logger.exception("Failed to copy default_config.py to %s:", options.configfile)

    config = confreader.Config(options.configfile)

    # XXX: the import is here because we need to call init_log
    # before start importing stuff
    from libqtile.core.manager import Qtile

    return Qtile(
        kore,
        config,
        no_spawn=options.no_spawn,
        state=options.state,
        socket_path=options.socket,
    )


def start(options):
    try:
        locale.setlocale(locale.LC_ALL, "")
    except locale.Error:
        pass

    libpath = (Path(__file__).parent / ".." / "..").resolve()
    logger.warning(f"Starting Qtile {VERSION} from {libpath}")
    rename_process()
    q = make_qtile(options)
    if q is None:
        logger.warning("Backend is missing required Python dependencies. Exiting.")
        exit(1)

    try:
        q.loop()
    except Exception:
        logger.exception("Qtile crashed")
        exit(1)
    logger.info("Exiting...")


def add_subcommand(subparsers, parents):
    parser = subparsers.add_parser("start", parents=parents, help="Start a Qtile session.")
    parser.add_argument(
        "-c",
        "--config",
        action="store",
        default=get_config_file(),
        dest="configfile",
        help="Use the specified configuration file.",
    )
    parser.add_argument(
        "-s",
        "--socket",
        action="store",
        default=None,
        dest="socket",
        help="Use specified socket for IPC.",
    )
    parser.add_argument(
        "-n",
        "--no-spawn",
        action="store_true",
        default=False,
        dest="no_spawn",
        help="Avoid spawning apps. (Used when restarting Qtile)",
    )
    parser.add_argument(
        "--with-state",
        default=None,
        dest="state",
        help="Pickled QtileState object. (Used when restarting Qtile).",
    )
    parser.add_argument(
        "-b",
        "--backend",
        default="x11",
        dest="backend",
        choices=libqtile.backend.CORES.keys(),
        help="Use specified backend.",
    )
    parser.set_defaults(func=start)
