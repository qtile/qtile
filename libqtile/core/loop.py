import asyncio
import contextlib
import signal
from typing import Awaitable, Optional

from libqtile.log_utils import logger


class QtileLoop(contextlib.AbstractAsyncContextManager):
    def __init__(self, qtile):
        super().__init__()
        self.qtile = qtile
        self._glib_loop: Optional[Awaitable] = None

    async def __aenter__(self) -> 'QtileLoop':
        loop = asyncio.get_running_loop()
        loop.add_signal_handler(signal.SIGINT, self.qtile.stop)
        loop.add_signal_handler(signal.SIGTERM, self.qtile.stop)
        loop.set_exception_handler(self._handle_exception)

        with contextlib.suppress(ImportError):
            self._glib_loop = self._setup_glib_loop()

        if self._glib_loop is None:
            logger.warning('importing dbus/gobject failed, dbus will not work.')
        return self

    async def __aexit__(self, *args) -> None:
        if self._glib_loop is not None:
            await self._teardown_glib_loop(self._glib_loop)
            self._glib_loop = None

        await self._cancel_all_tasks()

        loop = asyncio.get_running_loop()
        loop.remove_signal_handler(signal.SIGINT)
        loop.remove_signal_handler(signal.SIGTERM)
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
                await task()

    def _setup_glib_loop(self):
        # This is a little strange. python-dbus internally depends on gobject,
        # so gobject's threads need to be running, and a gobject 'main loop
        # thread' needs to be spawned, but we try to let it only interact with
        # us via calls to asyncio's call_soon_threadsafe.
        # We import dbus here to thrown an ImportError if it isn't
        # available. Since the only reason we're running this thread is
        # because of dbus, if dbus isn't around there's no need to run
        # this thread.
        import dbus  # noqa
        from gi.repository import GLib  # type: ignore

        def gobject_thread():
            ctx = GLib.main_context_default()
            while not self.qtile.is_stopped():
                try:
                    ctx.iteration(True)
                except Exception:
                    logger.exception('got exception from gobject')

        return asyncio.get_running_loop().run_in_executor(None, gobject_thread)

    async def _teardown_glib_loop(self, glib_loop):
        try:
            from gi.repository import GLib  # type: ignore
            GLib.idle_add(lambda: None)
            await glib_loop
        except ImportError:
            pass

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
                logger.exception(context['exception'])
        else:
            logger.error(f'unhandled error in event loop: {context["msg"]}')
