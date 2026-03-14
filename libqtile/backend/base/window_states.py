import enum


@enum.unique
class WindowStates(enum.Enum):
    TILED = 1
    FLOATING = 2
    MAXIMIZED = 3
    FULLSCREEN = 4
    TOP = 5
    MINIMIZED = 6
