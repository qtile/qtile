from .constants import *
from .context import Context as Context
from .patterns import (
    Gradient as Gradient,
    LinearGradient as LinearGradient,
    Pattern as Pattern,
    RadialGradient as RadialGradient,
    SolidPattern as SolidPattern,
    SurfacePattern as SurfacePattern,
)
from .surfaces import (
    ImageSurface as ImageSurface,
    RecordingSurface as RecordingSurface,
    Surface as Surface,
)
from .xcb import XCBSurface as XCBSurface
from typing import Any

VERSION: Any
version: str
version_info: Any

cairo: Any

class CairoError(Exception):
    status: Any = ...
    def __init__(self, message: Any, status: Any) -> None: ...

Error = CairoError
STATUS_TO_EXCEPTION: Any

OPERATOR_SOURCE: Any
