from abc import ABCMeta, abstractmethod

import typing
import asyncio

from . import xcbq


class ShutdownEvent:
    message: str

    def __init__(self, msg: str) -> None:
        self.message = msg


class Core(metaclass=ABCMeta):
    # We temporarily expose this object while we convert the manager. When the
    # Core object is complete, this will be removed.
    conn: xcbq.Connection

    @abstractmethod
    def start(self, display: str, loop: asyncio.AbstractEventLoop, q: asyncio.queues.Queue) -> None:
        pass

    @abstractmethod
    def get_keys(self) -> typing.List[str]:
        pass

    @abstractmethod
    def get_modifiers(self) -> typing.List[str]:
        pass
