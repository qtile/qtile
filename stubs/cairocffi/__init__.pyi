from typing import Any

from .constants import *
from .context import Context as Context
from .patterns import Gradient as Gradient
from .patterns import LinearGradient as LinearGradient
from .patterns import Pattern as Pattern
from .patterns import RadialGradient as RadialGradient
from .patterns import SolidPattern as SolidPattern
from .patterns import SurfacePattern as SurfacePattern
from .surfaces import ImageSurface as ImageSurface
from .surfaces import RecordingSurface as RecordingSurface
from .surfaces import Surface as Surface
from .xcb import XCBSurface as XCBSurface

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
