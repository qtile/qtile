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

import locale
import logging
import sys
from enum import Enum
from os import getenv, makedirs, path
from pathlib import Path
from typing import Optional

import typer
from typer import Option

import libqtile.backend
from libqtile import confreader
from libqtile.backend import Backends
from libqtile.log_utils import init_log, LogLevels, logger


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


def make_qtile(
    configfile: Path,
    socket: Optional[Path],
    backend: Backends,
    no_spawn: bool,
    with_state: Optional[str],
):

    kore = libqtile.backend.get_core(backend)

    if not configfile.is_file():
        try:
            makedirs(configfile.parent, exist_ok=True)
            from shutil import copyfile
            default_config_path = path.join(path.dirname(__file__),
                                            "..",
                                            "resources",
                                            "default_config.py")
            copyfile(default_config_path, configfile)
            logger.info('Copied default_config.py to %s', configfile)
        except Exception as e:
            logger.exception('Failed to copy default_config.py to %s: (%s)',
                             configfile, e)

    config = confreader.Config(configfile)

    # XXX: the import is here because we need to call init_log
    # before start importing stuff
    from libqtile.core.manager import Qtile
    return Qtile(
        kore,
        config,
        no_spawn=no_spawn,
        state=with_state,
        socket_path=socket,
    )


def start(
    config: Path = Option(confreader.path, "-c", "--config", help="Use the specified configuration file."),
    socket: Optional[Path] = Option(None, "-s", "--socket", help="Path of the Qtile IPC socket."),
    backend: Backends = Option(Backends.x11, "-b", "--backend", help="Use specified backend."),
    log_level: LogLevels = Option(
        LogLevels.WARNING, "-l", "--log-level", help="Set the log level.", case_sensitive=False
    ),
    no_spawn: bool = Option(False, "--no_spawn", help="Don't spawn apps (Used for restart)."),
    with_state: Optional[Path] = Option(None, help="State file (Used for restart)."),
) -> None:
    """
    Start Qtile.
    """
    try:
        locale.setlocale(locale.LC_ALL, locale.getdefaultlocale())
    except locale.Error:
        pass

    init_log(log_level=log_level.value, log_color=sys.stdout.isatty())

    rename_process()
    q = make_qtile(config, socket, backend, no_spawn, with_state)
    try:
        q.loop()
    except Exception:
        logger.exception('Qtile crashed')
        raise typer.Exit(code=1)
    logger.info('Exiting...')
