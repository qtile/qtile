import atexit
import enum
import os
import sys

from libqtile.log_utils import logger

__all__ = [
    "lifecycle",
]

Behavior = enum.Enum("Behavior", "NONE TERMINATE RESTART")


class LifeCycle:
    # This class exists mostly to move os.execv to the absolute last thing that
    # the python VM does before termination.
    # Be very careful about what references this class owns. Any object
    # referenced here when atexit fires will NOT be finalized properly.
    def __init__(self) -> None:
        self.behavior = Behavior.NONE
        self.state_file: str | None = None
        atexit.register(self._atexit)

    def _atexit(self) -> None:
        if self.behavior is Behavior.RESTART:
            argv = [sys.executable] + sys.argv
            if "--no-spawn" not in argv:
                argv.append("--no-spawn")
            argv = [s for s in argv if not s.startswith("--with-state")]
            if self.state_file is not None:
                argv.append("--with-state=" + self.state_file)
            logger.warning("Restarting Qtile with os.execv(...)")
            # No other code will execute after the following line does
            os.execv(sys.executable, argv)
        elif self.behavior is Behavior.TERMINATE:
            logger.warning("Qtile will now terminate")
        elif self.behavior is Behavior.NONE:
            pass


lifecycle = LifeCycle()
