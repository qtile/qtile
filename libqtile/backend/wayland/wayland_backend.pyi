from collections.abc import Callable

WLR_SILENT: int
WLR_ERROR: int
WLR_INFO: int
WLR_DEBUG: int

def hello() -> None: ...
def set_log_callback(verbosity: int, callback: Callable[[int, str], None]) -> None: ...
