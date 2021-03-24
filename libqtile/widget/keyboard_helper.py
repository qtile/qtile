#!/usr/bin/env python3
# pylint: disable=protected-access
import atexit
from functools import wraps
from itertools import zip_longest
from typing import AnyStr, List, NamedTuple

from libqtile.utils import logger
from libqtile.widget._keyboard_helper import ffi, lib

__all__ = ['VarDefsRec', 'LayoutRec', 'to_bytestr', 'connect_to_display', 'disconnect',
           'set_listen_to_events', 'get_group_index', 'set_group_index',
           'get_configured_layouts_record', 'get_configured_layouts']


class VarDefsRec(NamedTuple):
    """Hold the pythonized data of Xkb_VarDefsRec objects."""
    model: str  # char * model;
    layout: str  # char * layout;
    variant: str  # char * variant;
    options: str  # char * options;
    # sz_extra: int  # unsigned short sz_extra;
    # num_extra: int  # char * extra_names;
    # extra_names: str  # char * extra_names;
    # extra_values: int  # char ** extra_values;


class LayoutRec(NamedTuple):
    """Represent a layout that is or could be configured."""
    layout: str
    variant: str


def to_bytestr(cdata: ffi.CData):
    """Try to convert from char* to python bytes."""
    if not isinstance(cdata, ffi.CData):
        raise TypeError('Expected ffi.CData, got %r' % type(cdata))
    if cdata == ffi.NULL:
        return b''
    return ffi.string(cdata)


def ensure_connected(func):
    """Wrap a function to ensure a connection to X before func is run."""
    @wraps(func)
    def wrapped(*a, **kw):
        if not lib.display_is_open():
            raise ConnectionError('You must connect to a display first!')
        return func(*a, **kw)
    return wrapped


def connect_to_display(display: AnyStr):
    """Connect to a display."""
    if isinstance(display, str):
        connect_to_display(display.encode())
    if not isinstance(display, bytes):
        raise TypeError('display must be str or bytes, e.g. b":0"')
    ret = lib.open_display(display)
    if ret == lib.XkbOD_Success:
        return
    if ret == lib.XkbOD_ConnectionRefused:
        raise ConnectionError('Connection refused.')
    if ret == lib.XkbOD_BadLibraryVersion:
        raise ConnectionError('Incompatible Xkb library version.')
    if ret == lib.XkbOD_BadServerVersion:
        raise ConnectionError('Bad server version.')
    if ret == lib.XkbOD_NonXkbServer:
        raise ConnectionError('Server does not support Xkb.')
    logger.exception('Unexpected return value %d while connecting to X', ret)


def disconnect():
    """Disconnect if there is an active connection."""
    lib.close_display()


@ensure_connected
def set_listen_to_events():
    """Select the events to listen to (group change)."""
    lib._select_events()


@ensure_connected
def get_group_index() -> int:
    """Find the index of the active keyboard group."""
    return lib._get_group()


@ensure_connected
def set_group_index(group_num: int) -> bool:
    """
    Set the active keyboard group by its index.

    Returns True on success.
    """
    if not isinstance(group_num, int):
        raise ValueError('group_num must be an integer.')
    return bool(lib._set_group(group_num))


@ensure_connected
def get_configured_layouts_record() -> VarDefsRec:
    """Get a record containing the keyboard model, layouts, variants and options."""
    vdr = lib._get_layouts_variants()
    return VarDefsRec(
        to_bytestr(vdr.model).decode(),
        to_bytestr(vdr.layout).decode(),
        to_bytestr(vdr.variant).decode(),
        to_bytestr(vdr.options).decode(),
        # vdr.sz_extra, vdr.num_extra,
        # vdr.extra_names, vdr.extra_values
    )


def get_configured_layouts() -> List[LayoutRec]:
    """Return a list of configured layouts that is easier to handle than the raw record."""
    raw = get_configured_layouts_record()
    return [LayoutRec(lay, var) for lay, var in zip_longest(raw.layout.split(','),
                                                            raw.variant.split(','), fillvalue='')]


atexit.register(disconnect)
