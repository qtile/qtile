from __future__ import annotations

import asyncio
from unittest.mock import MagicMock

import pytest

from libqtile.backend.macos.idle import IdleNotifier
from test.backend.macos.fake_ffi import FakeFFI


class MockCore:
    def __init__(self):
        self.fake_ffi = FakeFFI()
        self._lib = self.fake_ffi.lib
        self._ffi = self.fake_ffi.ffi
        self.qtile = MagicMock()
        self.inhibited = False
        self.idle_inhibitor_manager = MagicMock()
        self.idle_inhibitor_manager.inhibited = False


@pytest.mark.asyncio
async def test_idle_notifier_polling():
    core = MockCore()
    idle = IdleNotifier(core)

    # Mock timers
    timer = MagicMock()
    timer.timeout = 5
    idle.add_timers([timer])

    # Initial state
    assert idle._fired == set()

    # User active, idle_time = 2
    core._lib.mac_get_idle_time.return_value = 2.0
    task = asyncio.create_task(idle._poll())
    await asyncio.sleep(0.1)
    assert 5 not in idle._fired

    # User idle, idle_time = 6
    core._lib.mac_get_idle_time.return_value = 6.0
    idle.fire_action = MagicMock()
    await asyncio.sleep(1.1)  # poll interval is 1s
    assert 5 in idle._fired
    idle.fire_action.assert_called_with(5)

    # User active again, idle_time = 0
    core._lib.mac_get_idle_time.return_value = 0.0
    await asyncio.sleep(1.1)
    assert 5 not in idle._fired
    # handle_resume should have been called (which calls fire_resume)

    task.cancel()


def test_idle_notifier_reset_clears_last_idle_time():
    """reset() must reset _last_idle_time to 0.0.

    Without this, previously-fired timeouts re-fire immediately after reset
    because _last_idle_time still holds the old high value.
    """
    core = MockCore()
    idle = IdleNotifier(core)

    # Simulate that idle time was high and we fired a timeout
    idle._last_idle_time = 30.0
    idle._fired.add(5)

    # reset() calls clear_timers() then start(); stub out start() so it's a no-op
    idle.start = MagicMock()
    idle.reset()

    assert idle._last_idle_time == 0.0, (
        f"_last_idle_time should be reset to 0.0, got {idle._last_idle_time}"
    )
    assert idle._fired == set(), "_fired should be cleared after reset()"
