from abc import ABCMeta, abstractmethod


class FloatStates:
    NOT_FLOATING = 1
    FLOATING = 2
    MAXIMIZED = 3
    FULLSCREEN = 4
    TOP = 5
    MINIMIZED = 6


class Window(metaclass=ABCMeta):
    def __init__(self):
        self.group = None
        self.state = None

    @abstractmethod
    def hide(self):
        pass

    @abstractmethod
    def has_fixed_size(self):
        pass


class Internal(metaclass=ABCMeta):
    pass


class Static(metaclass=ABCMeta):
    pass
