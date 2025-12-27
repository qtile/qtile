from libqtile.backend.base.idle_notify import IdleNotifier as BaseIdleNotifier

try:
    from libqtile.backend.wayland._ffi import lib
except ModuleNotFoundError:
    from libqtile.backend.wayland.ffi_stub import lib


class IdleNotifier(BaseIdleNotifier):
    def clear_timers(self) -> None:
        for timeout in self.timeouts:
            lib.qw_server_remove_idle_timer(self.core.qw, timeout)
        super().clear_timers()

    def run(self) -> None:
        for timeout in self.timeouts:
            lib.qw_server_add_idle_timer(self.core.qw, timeout)

    def handle_timeout(self, timeout: int) -> None:
        self.fire_action(timeout)

    def handle_resume(self) -> None:
        self.fire_resume()

    def reset(self) -> None:
        self.clear_timers()
        self.start()
