import logging
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


def init_log(log_level=logging.ERROR, logger='qtile', log_path='~/.%s.log'):
    log = getLogger(logger)
    log.setLevel(log_level)

    if log_path:
        log_path = os.path.expanduser(log_path)
        handler = logging.FileHandler(log_path)
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s %(levelname)s %(funcName)s:%(lineno)d %(message)s"
            )
        )
        log.addHandler(handler)

    handler = StreamHandler(sys.stderr)
    handler.setFormatter(
        ColorFormatter(
            '$RESET$COLOR%(asctime)s $BOLD$COLOR%(name)s'
            ' %(funcName)s:%(lineno)d $RESET %(message)s'
        )
    )
    log.addHandler(handler)

    log.warning('Starting %s' % logger.title())
    return log
