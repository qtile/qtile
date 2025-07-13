# Copyright (c) 2012 Florian Mounier
# Copyright (c) 2013-2014 Tao Sauvage
# Copyright (c) 2014 Sean Vig
# Copyright (c) 2014 roger
# Copyright (c) 2022 Matt Colligan
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

from __future__ import annotations

import os
import sys
import typing
import warnings
from logging import WARNING, Formatter, StreamHandler, captureWarnings, getLogger
from logging.handlers import RotatingFileHandler
from pathlib import Path

if typing.TYPE_CHECKING:
    from logging import Logger, LogRecord

logger = getLogger(__package__)


class ColorFormatter(Formatter):
    """Logging formatter adding console colors to the output."""

    black, red, green, yellow, blue, magenta, cyan, white = range(8)
    colors = {
        "WARNING": yellow,
        "INFO": green,
        "DEBUG": blue,
        "CRITICAL": yellow,
        "ERROR": red,
        "RED": red,
        "GREEN": green,
        "YELLOW": yellow,
        "BLUE": blue,
        "MAGENTA": magenta,
        "CYAN": cyan,
        "WHITE": white,
    }
    reset_seq = "\033[0m"
    color_seq = "\033[%dm"
    bold_seq = "\033[1m"

    def format(self, record: LogRecord) -> str:
        """Format the record with colors."""
        color = self.color_seq % (30 + self.colors[record.levelname])
        message = Formatter.format(self, record)
        message = (
            message.replace("$RESET", self.reset_seq)
            .replace("$BOLD", self.bold_seq)
            .replace("$COLOR", color)
        )
        for color, value in self.colors.items():
            message = (
                message.replace("$" + color, self.color_seq % (value + 30))
                .replace("$BG" + color, self.color_seq % (value + 40))
                .replace("$BG-" + color, self.color_seq % (value + 40))
            )
        return message + self.reset_seq


def get_default_log() -> Path:
    data_directory = os.path.expandvars("$XDG_DATA_HOME")
    if data_directory == "$XDG_DATA_HOME":
        # if variable wasn't set
        data_directory = os.path.expanduser("~/.local/share")

    qtile_directory = Path(data_directory) / "qtile"
    return qtile_directory / "qtile.log"


def init_log(
    log_level: int = WARNING,
    log_path: Path | None = None,
    log_size: int = 10000000,
    log_numbackups: int = 1,
    logger: Logger = logger,
) -> None:
    for handler in logger.handlers:
        logger.removeHandler(handler)

    if log_path is None or os.getenv("QTILE_XEPHYR"):
        # During tests or interactive xephyr development, log to stdout.
        handler = StreamHandler(sys.stdout)
        formatter: Formatter = ColorFormatter(
            "$RESET$COLOR%(asctime)s $BOLD$COLOR%(name)s "
            "%(filename)s:%(funcName)s():L%(lineno)d $RESET %(message)s"
        )

    else:
        # Otherwise during normal usage, log to file.
        try:
            log_path.parent.mkdir(parents=True, exist_ok=True)
        except PermissionError as e:
            # ok, only one place to write: stderr
            print(f"couldn't mkdir {log_path.parent}: {e}", file=sys.stderr)
            os._exit(1)

        handler = RotatingFileHandler(
            log_path,
            maxBytes=log_size,
            backupCount=log_numbackups,
        )
        formatter = Formatter(
            "%(asctime)s %(levelname)s %(name)s "
            "%(filename)s:%(funcName)s():L%(lineno)d %(message)s"
        )

    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(log_level)
    # Capture everything from the warnings module.
    captureWarnings(True)
    warnings.simplefilter("always")
    logger.debug("Starting logging for Qtile")
