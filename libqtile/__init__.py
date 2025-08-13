# Copyright (c) 2014 Sean Vig
# Copyright (c) 2014 Tycho Andersen
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
import asyncio
import ctypes.util
import enum


class _UndefinedCore:
    name = None


class _UndefinedQtile:
    core = _UndefinedCore()


qtile = _UndefinedQtile()
event_loop: asyncio.AbstractEventLoop


def init(q):
    global qtile
    qtile = q


class DynamicLibraries(enum.Enum):
    GOBJECT = "gobject-2.0"
    PANGO = "pango-1.0"
    PANGOCAIRO = "pangocairo-1.0"
    XCBCURSOR = "xcb-cursor"


def find_library(key: DynamicLibraries) -> str | None:
    # Some distros want to hard-code libpaths, BSDs generally want to resolve
    # things via ldconfig, and glibc has /etc/ld.so.cache. These last two are
    # handled by ctypes.util.find_library(), but the first one wants to be
    # specified at build time. So if it's been specified, let's use it.
    # Otherwise, just use ctypes.
    #
    # Finally, this module may not always be present, since during development
    # on a source tree, no install has actually taken place, so let's make its
    # presence optional.
    try:
        from . import _build_config

        attr = key.name + "_PATH"
        value = getattr(_build_config, attr, None)
        if value is not None:
            return value
    except ImportError:
        pass

    return ctypes.util.find_library(key.value)
