import enum


@enum.unique
class FloatStates(enum.Enum):
    NOT_FLOATING = 1
    FLOATING = 2
    MAXIMIZED = 3
    FULLSCREEN = 4
    TOP = 5
    MINIMIZED = 6
