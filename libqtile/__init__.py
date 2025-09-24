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
