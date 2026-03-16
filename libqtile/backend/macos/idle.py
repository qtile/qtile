from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from libqtile.backend.base.idle_notify import IdleNotifier as BaseIdleNotifier
from libqtile.utils import create_task

if TYPE_CHECKING:
    from libqtile.backend.macos.core import Core


class IdleNotifier(BaseIdleNotifier):
    def __init__(self, core: Core) -> None:
        super().__init__(core)
        self._task: asyncio.Task | None = None
        self._last_idle_time = 0.0
        self._fired: set[int] = set()

    def clear_timers(self) -> None:
        if self._task:
            self._task.cancel()
            self._task = None
        self._fired.clear()
        self._last_idle_time = 0.0
        super().clear_timers()

    def run(self) -> None:
        if not self.timeouts:
            return

        if self._task:
            self._task.cancel()

        self._task = create_task(self._poll())

    async def _poll(self) -> None:
        while True:
            idle_time = self.core._lib.mac_get_idle_time()

            if idle_time < self._last_idle_time:
                # User is active again
                if self._fired:
                    self.handle_resume()
                    self._fired.clear()

            self._last_idle_time = idle_time

            for timeout in self.timeouts:
                if timeout not in self._fired and idle_time >= timeout:
                    self.handle_timeout(timeout)
                    self._fired.add(timeout)

            await asyncio.sleep(1)

    def handle_timeout(self, timeout: int) -> None:
        self.fire_action(timeout)

    def handle_resume(self) -> None:
        self.fire_resume()

    def reset(self) -> None:
        self.clear_timers()
        self.start()
