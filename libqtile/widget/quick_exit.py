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

from enum import Enum, auto

from . import base
from .. import bar


class State(Enum):
    Neutral = auto()
    Counting = auto()


class QuickExit(base._TextBox):
    """
    A button of exiting the running qtile easily. When clicked this button, a countdown
    start. If the button pushed with in the countdown again, the qtile shutdown.
    """

    defaults = [
        ('default_text', '[ shutdown ]', 'A text displayed as a button'),
        ('countdown_format', '[ {} seconds ]', 'This text is showed when counting down.'),
        ('timer_interval', 1, 'A countdown interval.'),
        ('countdown_start', 5, 'Time to accept the second pushing.'),
    ]

    def __init__(self, widget=bar.CALCULATED, **config):
        base._TextBox.__init__(self, '', widget, **config)
        self.add_defaults(QuickExit.defaults)

        self.state = State.Neutral
        self.text = self.default_text
        self.countdown = self.countdown_start

    def update(self):
        if self.state == State.Neutral:
            return

        self.countdown -= 1
        if self.countdown < 0:
            self.state = State.Neutral
            self.countdown = self.countdown_start
            self.text = self.default_text
            self.draw()
            return

        self.text = self.countdown_format.format(self.countdown)
        self.timeout_add(self.timer_interval, self.update)
        self.draw()

    def button_press(self, x, y, button):
        if self.state == State.Neutral:
            self.state = State.Counting
            self.update()
            return

        if self.state == State.Counting:
            self.qtile.stop()
