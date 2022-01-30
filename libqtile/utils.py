# Copyright (c) 2008, Aldo Cortesi. All rights reserved.
# Copyright (c) 2020, Matt Colligan. All rights reserved.
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

from __future__ import annotations

import asyncio
import glob
import importlib
import os
import traceback
from collections import defaultdict
from collections.abc import Sequence
from random import randint
from shutil import which
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Union

    ColorType = Union[str, tuple[int, int, int], tuple[int, int, int, float]]
    ColorsType = Union[ColorType, list[ColorType]]

try:
    from dbus_next import Message, Variant
    from dbus_next.aio import MessageBus
    from dbus_next.constants import BusType, MessageType

    has_dbus = True
except ImportError:
    has_dbus = False

from libqtile.log_utils import logger


class QtileError(Exception):
    pass


def lget(o, v):
    try:
        return o[v]
    except (IndexError, TypeError):
        return None


def shuffle_up(lst):
    if len(lst) > 1:
        c = lst[-1]
        lst.remove(c)
        lst.insert(0, c)


def shuffle_down(lst):
    if len(lst) > 1:
        c = lst[0]
        lst.remove(c)
        lst.append(c)


def rgb(x: ColorType) -> tuple[float, float, float, float]:
    """
    Returns a valid RGBA tuple.

    Here are some valid specifications:
        #ff0000
        with alpha: #ff000080
        ff0000
        with alpha: ff0000.5
        (255, 0, 0)
        with alpha: (255, 0, 0, 0.5)

    Which is returned as (1.0, 0.0, 0.0, 0.5).
    """
    if isinstance(x, (tuple, list)):
        if len(x) == 4:
            alpha = x[-1]
        else:
            alpha = 1.0
        return (x[0] / 255.0, x[1] / 255.0, x[2] / 255.0, alpha)
    elif isinstance(x, str):
        if x.startswith("#"):
            x = x[1:]
        if "." in x:
            x, alpha_str = x.split(".")
            alpha = float("0." + alpha_str)
        else:
            alpha = 1.0
        if len(x) not in (6, 8):
            raise ValueError("RGB specifier must be 6 or 8 characters long.")
        vals = tuple(int(i, 16) for i in (x[0:2], x[2:4], x[4:6]))
        if len(x) == 8:
            alpha = int(x[6:8], 16) / 255.0
        vals += (alpha,)  # type: ignore
        return rgb(vals)  # type: ignore
    raise ValueError("Invalid RGB specifier.")


def hex(x):
    r, g, b, _ = rgb(x)
    return "#%02x%02x%02x" % (int(r * 255), int(g * 255), int(b * 255))


def has_transparency(colour: ColorsType):
    """
    Returns True if the colour is not fully opaque.

    Where a list of colours is passed, returns True if any
    colour is not fully opaque.
    """

    def has_alpha(col):
        return rgb(col)[3] < 1

    if isinstance(colour, (str, tuple)):
        return has_alpha(colour)

    elif isinstance(colour, list):
        return any([has_transparency(c) for c in colour])

    return False


def remove_transparency(colour: ColorsType):
    """
    Returns a tuple of (r, g, b) with no alpha.
    """

    def remove_alpha(col):
        stripped = tuple(x * 255.0 for x in rgb(col)[:3])
        return stripped

    if isinstance(colour, (str, tuple)):
        return remove_alpha(colour)

    elif isinstance(colour, list):
        return [remove_transparency(c) for c in colour]

    return (0, 0, 0)


def scrub_to_utf8(text):
    if not text:
        return ""
    elif isinstance(text, str):
        return text
    else:
        return text.decode("utf-8", "ignore")


def get_cache_dir():
    """
    Returns the cache directory and create if it doesn't exists
    """

    cache_directory = os.path.expandvars("$XDG_CACHE_HOME")
    if cache_directory == "$XDG_CACHE_HOME":
        # if variable wasn't set
        cache_directory = os.path.expanduser("~/.cache")
    cache_directory = os.path.join(cache_directory, "qtile")
    if not os.path.exists(cache_directory):
        os.makedirs(cache_directory)
    return cache_directory


def describe_attributes(obj, attrs, func=lambda x: x):
    """
    Helper for __repr__ functions to list attributes with truthy values only
    (or values that return a truthy value by func)
    """

    pairs = []

    for attr in attrs:
        value = getattr(obj, attr, None)
        if func(value):
            pairs.append("%s=%s" % (attr, value))

    return ", ".join(pairs)


def import_class(module_path, class_name, fallback=None):
    """Import a class safely

    Try to import the class module, and if it fails because of an ImporError
    it logs on WARNING, and logs the traceback on DEBUG level
    """
    try:
        module = importlib.import_module(module_path, __package__)
        return getattr(module, class_name)
    except ImportError as error:
        logger.warning("Unmet dependencies for '%s.%s': %s", module_path, class_name, error)
        if fallback:
            logger.debug("%s", traceback.format_exc())
            return fallback(module_path, class_name)
        raise


def lazify_imports(registry, package, fallback=None):
    """Leverage PEP 562 to make imports lazy in an __init__.py

    The registry must be a dictionary with the items to import as keys and the
    modules they belong to as a value.
    """
    __all__ = tuple(registry.keys())

    def __dir__():
        return __all__

    def __getattr__(name):
        if name not in registry:
            raise AttributeError
        module_path = "{}.{}".format(package, registry[name])
        return import_class(module_path, name, fallback=fallback)

    return __all__, __dir__, __getattr__


def send_notification(title, message, urgent=False, timeout=10000, id=None):
    """
    Send a notification.

    The id argument, if passed, requests the notification server to replace a visible
    notification with the same ID. An ID is returned for each call; this would then be
    passed when calling this function again to replace that notification. See:
    https://developer.gnome.org/notification-spec/
    """
    if not has_dbus:
        logger.warning("dbus-next is not installed. Unable to send notifications.")
        return -1

    id = randint(10, 1000) if id is None else id
    urgency = 2 if urgent else 1

    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        logger.warning("Eventloop has not started. Cannot send notification.")
    else:
        loop.create_task(_notify(title, message, urgency, timeout, id))

    return id


async def _notify(title, message, urgency, timeout, id):
    notification = [
        "qtile",  # Application name
        id,  # id
        "",  # icon
        title,  # summary
        message,  # body
        [],  # actions
        {"urgency": Variant("y", urgency)},  # hints
        timeout,
    ]  # timeout

    bus, msg = await _send_dbus_message(
        True,
        MessageType.METHOD_CALL,
        "org.freedesktop.Notifications",
        "org.freedesktop.Notifications",
        "/org/freedesktop/Notifications",
        "Notify",
        "susssasa{sv}i",
        notification,
    )

    if msg.message_type == MessageType.ERROR:
        logger.warning("Unable to send notification. " "Is a notification server running?")

    # a new bus connection is made each time a notification is sent so
    # we disconnect when the notification is done
    bus.disconnect()


def guess_terminal(preference=None):
    """Try to guess terminal."""
    test_terminals = []
    if isinstance(preference, str):
        test_terminals += [preference]
    elif isinstance(preference, Sequence):
        test_terminals += list(preference)
    test_terminals += [
        "roxterm",
        "sakura",
        "hyper",
        "alacritty",
        "terminator",
        "termite",
        "gnome-terminal",
        "konsole",
        "xfce4-terminal",
        "lxterminal",
        "mate-terminal",
        "kitty",
        "yakuake",
        "tilda",
        "guake",
        "eterm",
        "st",
        "urxvt",
        "xterm",
        "x-terminal-emulator",
    ]

    for terminal in test_terminals:
        logger.debug("Guessing terminal: {}".format(terminal))
        if not which(terminal, os.X_OK):
            continue

        logger.info("Terminal found: {}".format(terminal))
        return terminal

    logger.error("Default terminal has not been found.")


def scan_files(dirpath, *names):
    """
    Search a folder recursively for files matching those passed as arguments, with
    globbing. Returns a dict with keys equal to entries in names, and values a list of
    matching paths. E.g.:

    >>> scan_files('/wallpapers', '*.png', '*.jpg')
    defaultdict(<class 'list'>, {'*.png': ['/wallpapers/w1.png'], '*.jpg':
    ['/wallpapers/w2.jpg', '/wallpapers/w3.jpg']})

    """
    dirpath = os.path.expanduser(dirpath)
    files = defaultdict(list)

    for name in names:
        found = glob.glob(os.path.join(dirpath, "**", name), recursive=True)
        files[name].extend(found)

    return files


async def _send_dbus_message(
    session_bus, message_type, destination, interface, path, member, signature, body
):
    """
    Private method to send messages to dbus via dbus_next.

    Returns a tuple of the bus object and message response.
    """
    if session_bus:
        bus_type = BusType.SESSION
    else:
        bus_type = BusType.SYSTEM

    if isinstance(body, str):
        body = [body]

    bus = await MessageBus(bus_type=bus_type).connect()

    msg = await bus.call(
        Message(
            message_type=message_type,
            destination=destination,
            interface=interface,
            path=path,
            member=member,
            signature=signature,
            body=body,
        )
    )

    return bus, msg


async def add_signal_receiver(
    callback, session_bus=False, signal_name=None, dbus_interface=None, bus_name=None, path=None
):
    """
    Helper function which aims to recreate python-dbus's add_signal_receiver
    method in dbus_next with asyncio calls.

    Returns True if subscription is successful.
    """
    if not has_dbus:
        logger.warning("dbus-next is not installed. " "Unable to subscribe to signals")
        return False

    match_args = {
        "type": "signal",
        "sender": bus_name,
        "member": signal_name,
        "path": path,
        "interface": dbus_interface,
    }

    rule = ",".join("{}='{}'".format(k, v) for k, v in match_args.items() if v)

    bus, msg = await _send_dbus_message(
        session_bus,
        MessageType.METHOD_CALL,
        "org.freedesktop.DBus",
        "org.freedesktop.DBus",
        "/org/freedesktop/DBus",
        "AddMatch",
        "s",
        rule,
    )

    # Check if message sent successfully
    if msg.message_type == MessageType.METHOD_RETURN:
        bus.add_message_handler(callback)
        return True

    else:
        return False
