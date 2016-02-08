# Copyright (c) 2008, Aldo Cortesi. All rights reserved.
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

import os
import operator
import functools
import warnings

import six
from six.moves import reduce

from . import xcbq
from .log_utils import logger


class QtileError(Exception):
    pass


def lget(o, v):
    try:
        return o[v]
    except (IndexError, TypeError):
        return None


def translateMasks(modifiers):
    """
    Translate a modifier mask specified as a list of strings into an or-ed
    bit representation.
    """
    masks = []
    for i in modifiers:
        try:
            masks.append(xcbq.ModMasks[i])
        except KeyError:
            raise KeyError("Unknown modifier: %s" % i)
    if masks:
        return reduce(operator.or_, masks)
    else:
        return 0


def shuffleUp(lst):
    if len(lst) > 1:
        c = lst[-1]
        lst.remove(c)
        lst.insert(0, c)


def shuffleDown(lst):
    if len(lst) > 1:
        c = lst[0]
        lst.remove(c)
        lst.append(c)


class LRUCache(object):
    """
        A decorator that implements a self-expiring LRU cache for class
        methods (not functions!).

        Cache data is tracked as attributes on the object itself. There is
        therefore a separate cache for each object instance.
    """
    def __init__(self, size=100):
        self.size = size

    def __call__(self, f):
        cacheName = "_cached_%s" % f.__name__
        cacheListName = "_cachelist_%s" % f.__name__
        size = self.size

        @functools.wraps(f)
        def wrap(self, *args):
            if not hasattr(self, cacheName):
                setattr(self, cacheName, {})
                setattr(self, cacheListName, [])
            cache = getattr(self, cacheName)
            cacheList = getattr(self, cacheListName)
            if args in cache:
                cacheList.remove(args)
                cacheList.insert(0, args)
                return cache[args]
            else:
                ret = f(self, *args)
                cacheList.insert(0, args)
                cache[args] = ret
                if len(cacheList) > size:
                    d = cacheList.pop()
                    cache.pop(d)
                return ret
        return wrap


def rgb(x):
    """
        Returns a valid RGBA tuple.

        Here are some valid specifcations:
            #ff0000
            ff0000
            with alpha: ff0000.5
            (255, 0, 0)
            (255, 0, 0, 0.5)
    """
    if isinstance(x, tuple) or isinstance(x, list):
        if len(x) == 4:
            alpha = x[3]
        else:
            alpha = 1
        return (x[0] / 255.0, x[1] / 255.0, x[2] / 255.0, alpha)
    elif isinstance(x, six.string_types):
        if x.startswith("#"):
            x = x[1:]
        if "." in x:
            x, alpha = x.split(".")
            alpha = float("0." + alpha)
        else:
            alpha = 1
        if len(x) != 6:
            raise ValueError("RGB specifier must be 6 characters long.")
        vals = [int(i, 16) for i in (x[0:2], x[2:4], x[4:6])]
        vals.append(alpha)
        return rgb(vals)
    raise ValueError("Invalid RGB specifier.")


def hex(x):
    r, g, b, _ = rgb(x)
    return '#%02x%02x%02x' % (int(r * 255), int(g * 255), int(b * 255))


def scrub_to_utf8(text):
    if not text:
        return six.u("")
    elif isinstance(text, six.text_type):
        return text
    else:
        return text.decode("utf-8", "ignore")


# WARNINGS
class UnixCommandNotFound(Warning):
    pass


def catch_exception_and_warn(warning=Warning, return_on_exception=None,
                             excepts=Exception):
    """
    .. function:: warn_on_exception(func, [warning_class, return_on_failure,
            excepts])
        attempts to call func. catches exception or exception tuple and issues
        a warning instead. returns value of return_on_failure when the
        specified exception is raised.

        :param func: a callable to be wrapped
        :param warning: the warning class to issue if an exception is
            raised
        :param return_on_exception: the default return value of the function
            if an exception is raised
        :param excepts: an exception class (or tuple of exception classes) to
            catch during the execution of func
        :type excepts: Exception or tuple of Exception classes
        :type warning: Warning
        :rtype: a callable
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return_value = return_on_exception
            try:
                return_value = func(*args, **kwargs)
            except excepts as err:
                logger.warn(err.strerror)
                warnings.warn(err.strerror, warning)
            return return_value
        return wrapper
    return decorator


def get_cache_dir():
    """
    Returns the cache directory and create if it doesn't exists
    """

    cache_directory = os.path.expandvars('$XDG_CACHE_HOME')
    if cache_directory == '$XDG_CACHE_HOME':
        # if variable wasn't set
        cache_directory = os.path.expanduser("~/.cache")
    if not os.path.exists(cache_directory):
        os.makedirs(cache_directory)
    return cache_directory


def describe_attributes(obj, attrs, func=None):
    """
    Helper for __repr__ functions to list attributes with truthy values only
    (or values that return a truthy value by func)
    """

    if not func:
        func = lambda x: x  # flake8: noqa

    pairs = []

    for attr in attrs:
        value = getattr(obj, attr, None)
        if func(value):
            pairs.append('%s=%s' % (attr, value))

    return ', '.join(pairs)
