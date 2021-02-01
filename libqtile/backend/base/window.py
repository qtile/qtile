from abc import ABCMeta


class FloatStates:
    NOT_FLOATING = 1
    FLOATING = 2
    MAXIMIZED = 3
    FULLSCREEN = 4
    TOP = 5
    MINIMIZED = 6


class Window(metaclass=ABCMeta):
    pass


class Internal(metaclass=ABCMeta):
    pass


class Static(metaclass=ABCMeta):
    pass
