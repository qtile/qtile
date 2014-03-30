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
        self._widget_defaults.update({d[0]: d[1] for d in defaults})

    def __getattr__(self, name):
        found, value = self._find_default(name)
        if found:
            setattr(self, name, value)
            return value
        else:
            raise AttributeError("no attribute: %s" % name)

    def _find_default(self, name):
        """Returns a tuple (found, value)"""
        defaults = self._widget_defaults.copy()
        defaults.update(self.global_defaults)
        defaults.update(self._user_config)
        if name in defaults:
            return (True, defaults[name])
        else:
            return (False, None)


class ExtraFallback(object):
    """
        Adds another layer of fallback to attributes - to look up
        a different attribute name
    """

    def __init__(self, name, fallback):
        self.name = name
        self.hidden_attribute = "_" + name
        self.fallback = fallback

    def __get__(self, instance, owner=None):
        retval = getattr(instance, self.hidden_attribute, None)

        if not retval:
            _found, retval = Configurable._find_default(instance, self.name)

        if not retval:
            retval = getattr(instance, self.fallback, None)

        return retval

    def __set__(self, instance, value):
        """Set own value to a hidden attribute of the object"""
        setattr(instance, self.hidden_attribute, value)
