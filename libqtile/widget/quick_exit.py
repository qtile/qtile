# Copyright (c) 2019, Shunsuke Mie
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
from libqtile.command.base import expose_command
from libqtile.widget import base


class QuickExit(base._TextBox):
    """
    A button to shut down Qtile. When clicked, a countdown starts. Clicking
    the button again stops the countdown and prevents Qtile from shutting down.
    """

    defaults = [
        ("default_text", "[ shutdown ]", "The text displayed on the button."),
        ("countdown_format", "[ {} seconds ]", "The text displayed when counting down."),
        ("timer_interval", 1, "The countdown interval."),
        ("countdown_start", 5, "The number to count down from."),
    ]

    def __init__(self, **config):
        base._TextBox.__init__(self, "", **config)
        self.add_defaults(QuickExit.defaults)

        self.is_counting = False
        self.text = self.default_text
        self.countdown = self.countdown_start

        self.add_callbacks({"Button1": self.trigger})

    def __reset(self):
        self.is_counting = False
        self.countdown = self.countdown_start
        self.text = self.default_text
        self.timer.cancel()

    def update(self):
        if not self.is_counting:
            return

        self.countdown -= 1
        self.text = self.countdown_format.format(self.countdown)
        self.timer = self.timeout_add(self.timer_interval, self.update)
        self.draw()

        if self.countdown == 0:
            self.qtile.stop()
            return

    @expose_command()
    def trigger(self):
        if not self.is_counting:
            self.is_counting = True
            self.update()
        else:
            self.__reset()
            self.draw()
