from __future__ import annotations

import asyncio
import inspect
from collections.abc import Callable, Coroutine
from typing import TYPE_CHECKING

from libqtile.command import interface
from libqtile.lazy import LazyCall
from libqtile.utils import create_task, logger

if TYPE_CHECKING:
    pass


IdleAction = Callable | Coroutine | LazyCall | None


class IdleNotifier:
    def __init__(self, core):
        self.core = core
        self.timers = []

    def _run_action(self, action: IdleAction) -> None:
        if action is None:
            return

        if isinstance(action, LazyCall):
            if action.check(self.core.qtile):
                status, val = self.core.qtile.server.call(
                    (action.selectors, action.name, action.args, action.kwargs, False)
                )
                if status in (interface.ERROR, interface.EXCEPTION):
                    logger.error("IdleTimer command error %s: %s", action.name, val)
        elif inspect.iscoroutinefunction(action):
            create_task(action())
        elif asyncio.iscoroutine(action):
            create_task(action)
        else:
            try:
                action()
            except Exception:
                logger.exception("Error when trying to run idle timer command.")

    def fire_action(self, timeout: int) -> None:
        self.core.idle_inhibitor_manager.check()
        for timer in self.timers:
            if timer.timeout == timeout and timer.action is not None:
                if not (self.core.inhibited and timer.respect_inhibitor):
                    self._run_action(timer.action)
                    timer.fired = True

    def fire_resume(self) -> None:
        for timer in self.timers:
            if not timer.fired:
                continue

            if timer.resume is not None:
                self._run_action(timer.resume)

            timer.fired = False

    def add_timers(self, timers):
        self.timers = sorted(timers)

    @property
    def timeouts(self) -> list[int]:
        timeouts = []
        for timer in self.timers:
            if timer.timeout not in timeouts:
                timeouts.append(timer.timeout)

        return timeouts

    def start(self):
        self.clear_timers()

        self.add_timers(self.core.qtile.config.idle_timers)

        if not self.timers:
            return

        self.run()

    def run(self):
        raise NotImplementedError

    def clear_timers(self):
        self.timers = []
