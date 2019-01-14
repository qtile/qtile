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

from typing import Dict


class Configurable:
    global_defaults: Dict = {}

    def __init__(self, **config):
        self._variable_defaults = {}
        self._user_config = config

    def add_defaults(self, defaults):
        """Add defaults to this object, overwriting any which already exist"""
        # TODO: Ensure that d[1] is an immutable object? Otherwise an instance
        #       of this class could modify it also for all the other instances;
        #       if d[1] is a mutable object, perhaps fail or create a (shallow)
        #       copy, e.g. list(d[1]) in case of lists
        self._variable_defaults.update(dict((d[0], d[1]) for d in defaults))

    def __getattr__(self, name):
        if name == "_variable_defaults":
            raise AttributeError
        found, value = self._find_default(name)
        if found:
            setattr(self, name, value)
            return value
        else:
            cname = self.__class__.__name__
            raise AttributeError("%s has no attribute: %s" % (cname, name))

    def _find_default(self, name):
        """Returns a tuple (found, value)"""
        defaults = self._variable_defaults.copy()
        defaults.update(self.global_defaults)
        defaults.update(self._user_config)
        if name in defaults:
            return (True, defaults[name])
        else:
            return (False, None)


class ExtraFallback:
    """Adds another layer of fallback to attributes

    Used to look up a different attribute name
    """

    def __init__(self, name, fallback):
        self.name = name
        self.hidden_attribute = "_" + name
        self.fallback = fallback

    def __get__(self, instance, owner=None):
        retval = getattr(instance, self.hidden_attribute, None)

        if retval is None:
            _found, retval = Configurable._find_default(instance, self.name)

        if retval is None:
            retval = getattr(instance, self.fallback, None)

        return retval

    def __set__(self, instance, value):
        """Set own value to a hidden attribute of the object"""
        setattr(instance, self.hidden_attribute, value)
