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
from os import path, getenv

from libqtile.log_utils import init_log, logger
from libqtile import confreader

locale.setlocale(locale.LC_ALL, locale.getdefaultlocale())  # type: ignore

try:
    import pkg_resources
    VERSION = pkg_resources.require("qtile")[0].version
except (pkg_resources.DistributionNotFound, ImportError):
    VERSION = 'dev'


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


def make_qtile():
    from argparse import ArgumentParser
    parser = ArgumentParser(
        description='A full-featured, pure-Python tiling window manager.',
        prog='qtile',
    )
    parser.add_argument(
        '--version',
        action='version',
        version=VERSION,
    )
    parser.add_argument(
        "-c", "--config",
        action="store",
        default=path.expanduser(path.join(
            getenv('XDG_CONFIG_HOME', '~/.config'), 'qtile', 'config.py')),
        dest="configfile",
        help='Use the specified configuration file',
    )
    parser.add_argument(
        "-s", "--socket",
        action="store",
        default=None,
        dest="socket",
        help='Path to Qtile comms socket.'
    )
    parser.add_argument(
        "-n", "--no-spawn",
        action="store_true",
        default=False,
        dest="no_spawn",
        help='Avoid spawning apps. (Used for restart)'
    )
    parser.add_argument(
        '-l', '--log-level',
        default='WARNING',
        dest='log_level',
        choices=('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'),
        help='Set qtile log level'
    )
    parser.add_argument(
        '--with-state',
        default=None,
        dest='state',
        help='Pickled QtileState object (typically used only internally)',
    )
    options = parser.parse_args()
    log_level = getattr(logging, options.log_level)
    init_log(log_level=log_level)

    try:
        config = confreader.Config.from_file(options.configfile)
    except Exception as e:
        logger.exception('Error while reading config file (%s)', e)
        config = confreader.Config()
        from libqtile.widget import TextBox
        widgets = config.screens[0].bottom.widgets
        widgets.insert(0, TextBox('Config Err!'))
    # XXX: the import is here because we need to call init_log
    # before start importing stuff
    from libqtile.core import manager
    return manager.Qtile(
        config,
        fname=options.socket,
        no_spawn=options.no_spawn,
        state=options.state,
    )


def main():
    rename_process()
    q = make_qtile()
    try:
        q.loop()
    except Exception:
        logger.exception('Qtile crashed')
    logger.info('Exiting...')
