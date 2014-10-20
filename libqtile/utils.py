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

import operator
import functools

import six
from six.moves import reduce

from . import xcbq


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


class LRUCache:
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


def isStringLike(anobj):
    try:
        # Avoid succeeding expensively if anobj is large.
        anobj[:0] + ''
    except:
        return 0
    else:
        return 1


def isSequenceLike(anobj):
    """
        Is anobj a non-string sequence type (list, tuple, iterator, or
        similar)?  Crude, but mostly effective.
    """
    if not hasattr(anobj, "next"):
        if isStringLike(anobj):
            return 0
        try:
            anobj[:0]
        except:
            return 0
    return 1


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
    return '#%02x%02x%02x' % (r * 255, g * 255, b * 255)


def scrub_to_utf8(text):
    if not text:
        return six.u("")
    elif isinstance(text, six.text_type):
        return text
    else:
        return text.decode("utf-8", "ignore")
