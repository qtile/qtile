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
    log_size: int = 100_000,
    log_numbackups: int = 1,
    logger: Logger = logger,
) -> None:
    for handler in logger.handlers:
        logger.removeHandler(handler)

    stream_handler = StreamHandler(sys.stdout)
    stream_formatter = ColorFormatter(
        "$RESET$COLOR%(asctime)s $BOLD$COLOR%(name)s "
        "%(filename)s:%(funcName)s():L%(lineno)d $RESET %(message)s"
    )
    stream_handler.setFormatter(stream_formatter)
    logger.addHandler(stream_handler)

    if log_path is not None:
        try:
            log_path.parent.mkdir(parents=True, exist_ok=True)
        except PermissionError as e:
            print(f"couldn't mkdir {log_path.parent}: {e}", file=sys.stderr)
            os._exit(1)

        file_handler = RotatingFileHandler(
            log_path,
            maxBytes=log_size,
            backupCount=log_numbackups,
        )
        file_formatter = Formatter(
            "%(asctime)s %(levelname)s %(name)s "
            "%(filename)s:%(funcName)s():L%(lineno)d %(message)s"
        )

        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

    logger.setLevel(log_level)
    # Capture everything from the warnings module.
    captureWarnings(True)
    warnings.simplefilter("always")
    logger.debug("Starting logging for Qtile")
