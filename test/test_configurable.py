# vim: tabstop=4 shiftwidth=4 expandtab
# Copyright (c) 2015 Michael Killough
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

from libqtile import configurable


class ConfigurableWithFallback(configurable.Configurable):
    defaults = [
        ("foo", 3, ""),
    ]

    bar = configurable.ExtraFallback('bar', 'foo')

    def __init__(self, **config):
        configurable.Configurable.__init__(self, **config)
        self.add_defaults(self.defaults)


def test_use_fallback():
    c = ConfigurableWithFallback()
    assert c.foo == c.bar == 3

    c = ConfigurableWithFallback(foo=5)
    assert c.foo == c.bar == 5


def test_use_fallback_if_set_to_none():
    # Even if it is explicitly set to None, we should still
    # use the fallback. Could be useful if widget_defaults
    # were to set bar= and we wanted to specify that an
    # individual widget should fall back to using foo.
    c = ConfigurableWithFallback(foo=7, bar=None)
    assert c.foo == c.bar == 7

    c = ConfigurableWithFallback(foo=9)
    c.bar = None
    assert c.foo == c.bar == 9


def test_dont_use_fallback_if_set():
    c = ConfigurableWithFallback(bar=5)
    assert c.foo == 3
    assert c.bar == 5

    c = ConfigurableWithFallback(bar=0)
    assert c.foo == 3
    assert c.bar == 0

    c = ConfigurableWithFallback(foo=1, bar=2)
    assert c.foo == 1
    assert c.bar == 2

    c = ConfigurableWithFallback(foo=1)
    c.bar = 3
    assert c.foo == 1
    assert c.bar == 3
