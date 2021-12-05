# Copyright (c) 2021 elParaguayo
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
import libqtile.config
from libqtile.widget.base import _Widget


class TimerWidget(_Widget):

    def cmd_set_timer1(self):
        self.timer1 = self.timeout_add(10, self.cmd_set_timer1)

    def cmd_cancel_timer1(self):
        self.timer1.cancel()

    def cmd_set_timer2(self):
        self.timer2 = self.timeout_add(10, self.cmd_set_timer2)

    def cmd_cancel_timer2(self):
        self.timer2.cancel()

    def cmd_get_active_timers(self):
        active = [x for x in self._futures if x._scheduled]
        return len(active)


def test_multiple_timers(minimal_conf_noscreen, manager_nospawn):
    config = minimal_conf_noscreen
    config.screens = [
        libqtile.config.Screen(
            top=libqtile.bar.Bar([TimerWidget(10)], 10)
        )
    ]

    # Start manager and check no active timers
    manager_nospawn.start(config)
    assert manager_nospawn.c.widget["timerwidget"].get_active_timers() == 0

    # Start both timers and confirm both are active
    manager_nospawn.c.widget["timerwidget"].set_timer1()
    manager_nospawn.c.widget["timerwidget"].set_timer2()
    assert manager_nospawn.c.widget["timerwidget"].get_active_timers() == 2

    # Cancel timer1
    manager_nospawn.c.widget["timerwidget"].cancel_timer1()
    assert manager_nospawn.c.widget["timerwidget"].get_active_timers() == 1

    # Cancel timer2
    manager_nospawn.c.widget["timerwidget"].cancel_timer2()
    assert manager_nospawn.c.widget["timerwidget"].get_active_timers() == 0

    # Restart both timers
    manager_nospawn.c.widget["timerwidget"].set_timer1()
    manager_nospawn.c.widget["timerwidget"].set_timer2()
    assert manager_nospawn.c.widget["timerwidget"].get_active_timers() == 2

    # Verify that `finalize()` cancels all timers.
    manager_nospawn.c.widget["timerwidget"].eval("self.finalize()")
    assert manager_nospawn.c.widget["timerwidget"].get_active_timers() == 0
