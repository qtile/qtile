# Copyright (c) 2012 Florian Mounier
# Copyright (c) 2013-2014 Tao Sauvage
# Copyright (c) 2014 Sean Vig
# Copyright (c) 2014 roger
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
#
# vim: tabstop=4 shiftwidth=4 expandtab

from logging import getLogger, StreamHandler, Formatter, WARNING, captureWarnings
from logging.handlers import RotatingFileHandler
_logger = getLogger(__name__)
import os
import sys
import warnings


class ColorFormatter(Formatter):
    """Logging formatter adding console colors to the output."""
    black, red, green, yellow, blue, magenta, cyan, white = range(8)
    colors = {
        'WARNING': yellow,
        'INFO': green,
        'DEBUG': blue,
        'CRITICAL': yellow,
        'ERROR': red,
        'RED': red,
        'GREEN': green,
        'YELLOW': yellow,
        'BLUE': blue,
        'MAGENTA': magenta,
        'CYAN': cyan,
        'WHITE': white
    }
    reset_seq = '\033[0m'
    color_seq = '\033[%dm'
    bold_seq = '\033[1m'

    def format(self, record):
        """Format the record with colors."""
        color = self.color_seq % (30 + self.colors[record.levelname])
        message = Formatter.format(self, record)
        message = message.replace('$RESET', self.reset_seq)\
            .replace('$BOLD', self.bold_seq)\
            .replace('$COLOR', color)
        for color, value in self.colors.items():
            message = message.replace(
                '$' + color, self.color_seq % (value + 30))\
                .replace('$BG' + color, self.color_seq % (value + 40))\
                .replace('$BG-' + color, self.color_seq % (value + 40))
        return message + self.reset_seq


def init_log(log_level=WARNING, logger='qtile', log_path='~/.%s.log',
             truncate=False, log_size=10000000, log_numbackups=1, log_color=True, ):
    log = getLogger()
    if log_path:
        try:
            log_path = log_path % logger
        except TypeError:  # Happens if log_path doesn't contain formatters.
            pass
        log_path = os.path.expanduser(log_path)
        if truncate:
            with open(log_path, "w"):
                pass
        handler = RotatingFileHandler(
            log_path,
            maxBytes=log_size,
            backupCount=log_numbackups
        )
    else:
        handler = StreamHandler(sys.stdout)
    if log_color:
        handler.setFormatter(
            ColorFormatter(
                '$RESET$COLOR%(asctime)s $BOLD$COLOR%(name)s'
                ' %(funcName)s:%(lineno)d $RESET %(message)s'
            )
        )
    else:
        handler.setFormatter(
            Formatter(
                "%(asctime)s %(levelname)s %(funcName)s:%(lineno)d %(message)s"
            )
        )
    log.addHandler(handler)
    log.setLevel(log_level)
    # Capture everything from the warnings module.
    captureWarnings(True)
    warnings.simplefilter("always")
    _logger.warning('Starting logging for %s' % logger)
    return _logger

