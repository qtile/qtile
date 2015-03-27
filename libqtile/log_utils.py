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

import logging
import logging.handlers
import os
import sys
from logging import getLogger, StreamHandler


class ColorFormatter(logging.Formatter):
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
        message = logging.Formatter.format(self, record)
        message = message.replace('$RESET', self.reset_seq)\
            .replace('$BOLD', self.bold_seq)\
            .replace('$COLOR', color)
        for color, value in self.colors.items():
            message = message.replace(
                '$' + color, self.color_seq % (value + 30))\
                .replace('$BG' + color, self.color_seq % (value + 40))\
                .replace('$BG-' + color, self.color_seq % (value + 40))
        return message + self.reset_seq


def init_log(log_level=logging.WARNING, logger='qtile', log_path='~/.%s.log'):
    log = getLogger(logger)
    log.setLevel(log_level)

    if log_path:
        try:
            log_path = log_path % logger
        except TypeError:  # Happens if log_path doesn't contain formatters.
            pass
        log_path = os.path.expanduser(log_path)
        with open(log_path, "aw"):
            pass
        handler = logging.handlers.RotatingFileHandler(
              log_path, maxBytes=1073741824)
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s %(levelname)s %(funcName)s:%(lineno)d %(message)s"
            )
        )
        log.addHandler(handler)

    handler = StreamHandler(sys.stdout)
    handler.setFormatter(
        ColorFormatter(
            '$RESET$COLOR%(asctime)s $BOLD$COLOR%(name)s'
            ' %(funcName)s:%(lineno)d $RESET %(message)s'
        )
    )
    log.addHandler(handler)

    log.warning('Starting %s' % logger.title())
    return log
