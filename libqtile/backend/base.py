import typing
from abc import ABCMeta, abstractmethod


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
