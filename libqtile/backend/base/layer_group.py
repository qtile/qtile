from enum import IntEnum, auto


class LayerGroup(IntEnum):
    """
    Helper object to specify stacking layers. `LayerGroup` is backend-agnostic,
    so backends will need to map behaviour accordingly. However, a common object
    allows us have more common code across backends.
    """

    BACKGROUND = 1
    BOTTOM = auto()
    KEEP_BELOW = auto()
    INTERNAL = auto()
    LAYOUT = auto()
    KEEP_ABOVE = auto()
    MAX = auto()
    FULLSCREEN = auto()
    BRING_TO_FRONT = auto()
    TOP = auto()
    OVERLAY = auto()
    SYSTEM = auto()
