import typing
from abc import ABCMeta, abstractmethod

from libqtile import config


class Core(metaclass=ABCMeta):
    @property
    @abstractmethod
    def display_name(self) -> str:
        pass

    @abstractmethod
    def get_keys(self) -> typing.List[str]:
        pass

    @abstractmethod
    def get_modifiers(self) -> typing.List[str]:
        pass

    @abstractmethod
    def grab_key(self, key: config.Key) -> typing.Tuple[int, int]:
        """Configure the backend to grab the key event"""

    @abstractmethod
    def ungrab_key(self, key: config.Key) -> typing.Tuple[int, int]:
        """Release the given key event"""

    @abstractmethod
    def ungrab_keys(self) -> None:
        """Release the grabbed key events"""

    @abstractmethod
    def grab_button(self, mouse: config.Mouse) -> None:
        """Configure the backend to grab the mouse event"""

    @abstractmethod
    def ungrab_buttons(self) -> None:
        """Release the grabbed button events"""

    @abstractmethod
    def grab_pointer(self) -> None:
        """Configure the backend to grab mouse events"""

    @abstractmethod
    def ungrab_pointer(self) -> None:
        """Release grabbed pointer events"""
