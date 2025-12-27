import xcffib.screensaver

from libqtile.backend.base.idle_notify import IdleNotifier as BaseIdleNotifier
from libqtile.log_utils import logger


class IdleNotifier(BaseIdleNotifier):
    def __init__(self, core):
        super().__init__(core)
        self.has_screen_saver = hasattr(self.core.conn, "mit_screen_saver")

    @property
    def timeout_increments(self):
        timers = self.timeouts
        return [timers[0]] + [timers[i] - timers[i - 1] for i in range(1, len(timers))]

    @property
    def has_timeout(self):
        return self.timeouts and self.index < len(self.timeouts)

    def run(self):
        if not self.has_screen_saver:
            logger.warning(
                "Idle timers need the screensaver extension for x11. Timers will not be run."
            )
            return

        if not self.timeouts:
            return

        self.core.conn.mit_screen_saver.select_events(self.core._root.wid)
        self.reset()

    def reset(self):
        self.index = 0
        if self.has_timeout:
            self.set_timer()

    def set_timer(self):
        interval = self.timeout_increments[self.index]
        self.core.conn.mit_screen_saver.set_interval(interval)

    def handle_timeout(self):
        timeout = self.timeouts[self.index]
        self.fire_action(timeout)

        self.index += 1
        if self.has_timeout:
            self.set_timer()

    def handle_resume(self):
        if self.index > 0:
            self.fire_resume()

        self.reset()

    def check_event(self, event) -> bool:
        if not self.has_screen_saver:
            return False

        if type(event) is not xcffib.screensaver.NotifyEvent:
            return False

        if self.has_timeout and event.state in (
            xcffib.screensaver.State.On,
            xcffib.screensaver.State.Cycle,
        ):
            self.handle_timeout()
        elif event.state == xcffib.screensaver.State.Off:
            self.handle_resume()

        return True

    def clear_timers(self) -> None:
        super().clear_timers()
        self.reset()
