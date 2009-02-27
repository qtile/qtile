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

import operator, functools
from Xlib import X
import manager

import sys

_modmasks = {
    "shift":    X.ShiftMask,
    "lock":     X.LockMask,
    "control":  X.ControlMask,
    "mod1":     X.Mod1Mask,
    "mod2":     X.Mod2Mask,
    "mod3":     X.Mod3Mask,
    "mod4":     X.Mod4Mask,
    "mod5":     X.Mod5Mask,
}


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
            masks.append(_modmasks[i])
        except KeyError:
            raise manager.QtileError("Unknown modifier: %s"%i)
    return reduce(operator.or_, masks) if masks else 0


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
        cacheName = "_cached_%s"%f.__name__
        cacheListName = "_cachelist_%s"%f.__name__
        size = self.size

        @functools.wraps(f)
        def wrap(self, *args):
            if not hasattr(self, cacheName):
                setattr(self, cacheName, {})
                setattr(self, cacheListName, [])
            cache = getattr(self, cacheName)
            cacheList = getattr(self, cacheListName)
            if cache.has_key(args):
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
