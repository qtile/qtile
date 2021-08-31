from __future__ import annotations

import asyncio
import contextlib
import signal
from typing import Callable, Dict, Optional, TYPE_CHECKING

from libqtile.log_utils import logger

if TYPE_CHECKING:
    from libqtile.core.manager import Qtile

class LoopContext(contextlib.AbstractAsyncContextManager):
    def __init__(
        self,
        signals: Optional[Dict[signal.Signals, Callable]] = None,
    ) -> None:
        super().__init__()
        self._signals = signals or {}
        self._stopped = False

    async def __aenter__(self) -> 'LoopContext':
        self._stopped = False
        loop = asyncio.get_running_loop()
        loop.set_exception_handler(self._handle_exception)
        for sig, handler in self._signals.items():
            loop.add_signal_handler(sig, handler)

        return self

    async def __aexit__(self, *args) -> None:
        self._stopped = True

        await self._cancel_all_tasks()

        loop = asyncio.get_running_loop()
        map(loop.remove_signal_handler, self._signals.keys())
        loop.set_exception_handler(None)

    async def _cancel_all_tasks(self):
        # we don't want to cancel this task, so filter all_tasks
        # generator to filter in place
        pending = (
            task for task in asyncio.all_tasks()
            if task is not asyncio.current_task()
        )
        for task in pending:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task

    def _handle_exception(
        self,
        loop: asyncio.AbstractEventLoop,
        context: dict,
    ) -> None:
        # message is always present, but we'd prefer the exception if available
        if 'exception' in context:
            exc = context['exception']
            # CancelledErrors happen when we simply cancel the main task during
            # a normal restart procedure
            if not isinstance(exc, asyncio.CancelledError):
                logger.exception(exc)
        else:
            logger.error(f'unhandled error in event loop: {context["msg"]}')


class QtileEventLoopPolicy(asyncio.DefaultEventLoopPolicy):  # type: ignore
    """
    Asyncio policy to ensure the main event loop is accessible
    even if `get_event_loop()` is called from a different thread.
    """

    def __init__(self, qtile: Qtile) -> None:
        asyncio.DefaultEventLoopPolicy.__init__(self)
        self.qtile = qtile

    def get_event_loop(self) -> asyncio.AbstractEventLoop:
        if isinstance(self.qtile._eventloop, asyncio.AbstractEventLoop):
            return self.qtile._eventloop

        raise RuntimeError
