from .surfaces import Surface as Surface
from typing import Any

class XCBSurface(Surface):
    def __init__(
        self, conn: Any, drawable: Any, visual: Any, width: Any, height: Any
    ) -> None: ...
    def set_size(self, width: Any, height: Any) -> None: ...
