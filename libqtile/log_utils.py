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

from logging import getLogger, StreamHandler, Formatter, WARNING, captureWarnings
from logging.handlers import RotatingFileHandler
import os
import sys
import warnings

logger = getLogger(__package__)


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


def init_log(log_level=WARNING, log_path='~/.%s.log', log_truncate=False,
             log_size=10000000, log_numbackups=1, log_color=True):
    formatter = Formatter(
        "%(asctime)s %(levelname)s %(name)s %(filename)s:%(funcName)s():L%(lineno)d %(message)s"
    )

    # We'll always use a stream handler
    stream_handler = StreamHandler(sys.stdout)
    if log_color:
        color_formatter = ColorFormatter(
            '$RESET$COLOR%(asctime)s $BOLD$COLOR%(name)s %(filename)s:%(funcName)s():L%(lineno)d $RESET %(message)s'
        )
        stream_handler.setFormatter(color_formatter)
    else:
        stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    # If we have a log path, we'll also setup a log file
    if log_path:
        try:
            log_path %= 'qtile'
        except TypeError:  # Happens if log_path doesn't contain formatters.
            pass
        log_path = os.path.expanduser(log_path)
        if log_truncate:
            with open(log_path, "w"):
                pass
        file_handler = RotatingFileHandler(
            log_path,
            maxBytes=log_size,
            backupCount=log_numbackups
        )

        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    logger.setLevel(log_level)
    # Capture everything from the warnings module.
    captureWarnings(True)
    warnings.simplefilter("always")
    logger.warning('Starting logging for Qtile')
    return logger
