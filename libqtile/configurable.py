# Copyright (c) 2012, Tycho Andersen. All rights reserved.
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


class Configurable(object):
    global_defaults = {}

    def __init__(self, **config):
        self._widget_defaults = {}
        self._user_config = config

    def add_defaults(self, defaults):
        """
            Add defaults to this object, overwriting any which already exist.
        """
        for (prop, value, _) in defaults:
            self._widget_defaults[prop] = value

    def __getattr__(self, name):
        try:
            return self._user_config[name]
        except KeyError:
            try:
                return self.global_defaults[name]
            except KeyError:
                try:
                    return self._widget_defaults[name]
                except KeyError:
                    raise AttributeError("no attribute: %s" % name)
