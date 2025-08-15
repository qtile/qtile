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
from pathlib import Path
from random import randint
from shutil import which
from typing import TYPE_CHECKING

try:
    from dbus_fast import AuthError, Message, Variant
    from dbus_fast.aio import MessageBus
    from dbus_fast.constants import BusType, MessageType

    has_dbus = True
except ImportError:
    has_dbus = False

import libqtile
from libqtile.log_utils import logger

ColorType = str | tuple[int, int, int] | tuple[int, int, int, float]
ColorsType = ColorType | list[ColorType]
if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine
    from typing import Any, TypeVar

    T = TypeVar("T")

dbus_bus_connections = set()

# Create a list to collect references to tasks so they're not garbage collected
# before they've run
TASKS: list[asyncio.Task[None]] = []


def create_task(coro: Coroutine) -> asyncio.Task | None:
    """
    Wrapper for asyncio.create_task.

    Stores task so garbage collector doesn't remove it and removes reference when it's done.
    See: https://textual.textualize.io/blog/2023/02/11/the-heisenbug-lurking-in-your-async-code/
    for more info about the issue this solves.
    """
    loop = asyncio.get_running_loop()
    if not loop:
        return None

    def tidy(task: asyncio.Task) -> None:
        TASKS.remove(task)

    task = asyncio.create_task(coro)
    TASKS.append(task)
    task.add_done_callback(tidy)

    return task


def cancel_tasks() -> None:
    """Cancel scheduled tasks."""
    for task in TASKS:
        task.cancel()


class QtileError(Exception):
    pass


def lget(o: list[T], v: int) -> T | None:
    try:
        return o[v]
    except (IndexError, TypeError):
        return None


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
    if isinstance(x, tuple | list):
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
        if len(x) not in (3, 6, 8):
            raise ValueError("RGB specifier must be 3, 6 or 8 characters long.")
        if len(x) == 3:
            # Multiplying by 17: 0xA * 17 = 0xAA etc.
            vals = tuple(int(i, 16) * 17 for i in x)
        else:
            vals = tuple(int(i, 16) for i in (x[0:2], x[2:4], x[4:6]))
        if len(x) == 8:
            alpha = int(x[6:8], 16) / 255.0
        vals += (alpha,)  # type: ignore
        return rgb(vals)  # type: ignore
    raise ValueError("Invalid RGB specifier.")


def hex(x: ColorType) -> str:
    r, g, b, _ = rgb(x)
    return f"#{int(r * 255):02x}{int(g * 255):02x}{int(b * 255):02x}"


def has_transparency(colour: ColorsType) -> bool:
    """
    Returns True if the colour is not fully opaque.

    Where a list of colours is passed, returns True if any
    colour is not fully opaque.
    """
    if isinstance(colour, str | tuple):
        return rgb(colour)[3] < 1
    return any(has_transparency(c) for c in colour)


def remove_transparency(colour: ColorsType):  # type: ignore
    """
    Returns a tuple of (r, g, b) with no alpha.
    """
    if isinstance(colour, str | tuple):
        return tuple(x * 255.0 for x in rgb(colour)[:3])
    return [remove_transparency(c) for c in colour]


def is_valid_colors(color: ColorsType) -> bool:
    """
    Returns whether the argument is a valid color or list of colors.
    """
    if not isinstance(color, list):
        color = [color]
    try:
        list(rgb(c) for c in color)
        return True
    except (ValueError, TypeError):
        return False


def scrub_to_utf8(text: str | bytes) -> str:
    if not text:
        return ""
    elif isinstance(text, str):
        return text
    else:
        return text.decode("utf-8", "ignore")


def get_cache_dir() -> str:
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


def get_config_file() -> Path:
    config_home = Path(os.getenv("XDG_CONFIG_HOME", "~/.config")).expanduser()
    config_file = config_home.joinpath("qtile/config.py")
    if config_file.exists():
        return config_file

    xdg_config_dirs = os.getenv("XDG_CONFIG_DIRS", "/etc/xdg/").split(":")
    for config_dir in xdg_config_dirs:
        system_wide_config = Path(config_dir).expanduser().joinpath("qtile/config.py")
        if system_wide_config.exists():
            return system_wide_config

    return config_file


def describe_attributes(obj: Any, attrs: list[str], func: Callable = lambda x: x) -> str:
    """
    Helper for __repr__ functions to list attributes with truthy values only
    (or values that return a truthy value by func)
    """

    pairs = []

    for attr in attrs:
        value = getattr(obj, attr, None)
        if func(value):
            pairs.append(f"{attr}={value}")

    return ", ".join(pairs)


def import_class(
    module_path: str,
    class_name: str,
    fallback: Callable | None = None,
) -> Any:
    """Import a class safely

    Try to import the class module, and if it fails because of an ImportError
    it logs on WARNING, and logs the traceback on DEBUG level
    """
    try:
        module = importlib.import_module(module_path, __package__)
        return getattr(module, class_name)
    except ImportError:
        logger.exception("Unmet dependencies for '%s.%s':", module_path, class_name)
        if fallback:
            logger.debug("%s", traceback.format_exc())
            return fallback(module_path, class_name)
        raise


def lazify_imports(
    registry: dict[str, str],
    package: str,
    fallback: Callable | None = None,
) -> tuple[tuple[str, ...], Callable, Callable]:
    """Leverage PEP 562 to make imports lazy in an __init__.py

    The registry must be a dictionary with the items to import as keys and the
    modules they belong to as a value.
    """
    __all__ = tuple(registry.keys())

    def __dir__() -> tuple[str, ...]:  # noqa: N807
        return __all__

    def __getattr__(name: str) -> Any:  # noqa: N807
        if name not in registry:
            raise AttributeError
        module_path = f"{package}.{registry[name]}"
        return import_class(module_path, name, fallback=fallback)

    return __all__, __dir__, __getattr__


def send_notification(
    title: str,
    message: str,
    urgent: bool = False,
    timeout: int = -1,
    id_: int | None = None,
) -> int:
    """
    Send a notification.

    The id_ argument, if passed, requests the notification server to replace a visible
    notification with the same ID. An ID is returned for each call; this would then be
    passed when calling this function again to replace that notification. See:
    https://developer.gnome.org/notification-spec/
    """
    if "PYTEST_CURRENT_TEST" in os.environ:
        logger.warning("skipped notification because we are in tests")
        return -1
    if not has_dbus:
        logger.warning("dbus-fast is not installed. Unable to send notifications.")
        return -1

    id_ = randint(10, 1000) if id_ is None else id_
    urgency = 2 if urgent else 1

    loop = libqtile.event_loop
    loop.create_task(_notify(title, message, urgency, timeout, id_))

    return id_


async def _notify(
    title: str,
    message: str,
    urgency: int,
    timeout: int,
    id_: int,
) -> None:
    notification = [
        "qtile",  # Application name
        id_,  # id
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

    if msg and msg.message_type == MessageType.ERROR:
        logger.warning("Unable to send notification. Is a notification server running?")

    # a new bus connection is made each time a notification is sent so
    # we disconnect when the notification is done
    if bus:
        bus.disconnect()


def guess_terminal(preference: str | Sequence | None = None) -> str | None:
    """Try to guess terminal."""
    test_terminals = []
    if isinstance(preference, str):
        test_terminals += [preference]
    elif isinstance(preference, Sequence):
        test_terminals += list(preference)
    if "WAYLAND_DISPLAY" in os.environ:
        # Wayland-only terminals
        test_terminals += ["foot"]
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
        "ghostty",
        "yakuake",
        "tilda",
        "guake",
        "eterm",
        "st",
        "urxvt",
        "wezterm",
        "xterm",
        "x-terminal-emulator",
    ]

    for terminal in test_terminals:
        logger.debug("Guessing terminal: %s", terminal)
        if not which(terminal, os.X_OK):
            continue

        logger.info("Terminal found: %s", terminal)
        return terminal

    logger.error("Default terminal has not been found.")
    return None


def scan_files(dirpath: str, *names: str) -> defaultdict[str, list[str]]:
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
    session_bus: bool,
    message_type: MessageType,
    destination: str | None,
    interface: str | None,
    path: str | None,
    member: str | None,
    signature: str,
    body: Any,
    negotiate_unix_fd: bool = False,
    bus: MessageBus | None = None,
    preserve: bool = False,
) -> tuple[MessageBus | None, Message | None]:
    """
    Private method to send messages to dbus via dbus_fast.

    An existing bus connection can be passed, if left empty, a new
    bus connection will be created.

    Returns a tuple of the bus object and message response.
    """
    if bus is None:
        if session_bus:
            bus_type = BusType.SESSION
        else:
            bus_type = BusType.SYSTEM

        try:
            bus = await MessageBus(
                bus_type=bus_type, negotiate_unix_fd=negotiate_unix_fd
            ).connect()
        except (AuthError, Exception):
            logger.warning("Unable to connect to dbus.")
            return None, None

    if isinstance(body, str):
        body = [body]

    # Ignore types here: dbus-fast has default values of `None` for certain
    # parameters but the signature is `str` so passing `None` results in an
    # error in mypy.
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

    # Keep details of bus connections so we can close them on exit
    # dbus_bus_connetions is a set so we don't need to worry about
    # duplicates
    if not preserve:
        dbus_bus_connections.add(bus)

    return bus, msg


async def add_signal_receiver(
    callback: Callable,
    session_bus: bool = False,
    signal_name: str | None = None,
    dbus_interface: str | None = None,
    bus_name: str | None = None,
    path: str | None = None,
    check_service: bool = False,
    use_bus: MessageBus | None = None,
    preserve: bool = False,
) -> bool:
    """
    Helper function which aims to recreate python-dbus's add_signal_receiver
    method in dbus_fast with asyncio calls.

    If check_service is `True` the method will raise a wanrning and return False
    if the service is not visible on the bus. If the `bus_name` is None, no
    check will be performed.

    Returns True if subscription is successful.
    """
    if not has_dbus:
        logger.warning("dbus-fast is not installed. Unable to subscribe to signals")
        return False

    if bus_name and check_service:
        found = await find_dbus_service(bus_name, session_bus)
        if not found:
            logger.warning(
                "The %s name was not found on the bus. No callback will be attached.", bus_name
            )
            return False

    match_args = {
        "sender": bus_name,
        "member": signal_name,
        "path": path,
        "interface": dbus_interface,
    }

    rule = "type='signal',"
    rule += ",".join(f"{k}='{v}'" for k, v in match_args.items() if v)

    logger.debug("Adding dbus match rule: %s", rule)

    bus, msg = await _send_dbus_message(
        session_bus,
        MessageType.METHOD_CALL,
        "org.freedesktop.DBus",
        "org.freedesktop.DBus",
        "/org/freedesktop/DBus",
        "AddMatch",
        "s",
        [rule],
        bus=use_bus,
        preserve=preserve,
    )

    # Check if message sent successfully
    if bus and msg and msg.message_type == MessageType.METHOD_RETURN:

        def match_message(msg: Message, match_args: dict[str, str | None]) -> bool:
            return all(getattr(msg, k) == v for k, v in match_args.items() if v)

        async def resolve_sender(signal_msg: Message) -> tuple[str, Message]:
            """Looks up a pretty bus name to retrieve the unique name."""
            _, sender_msg = await _send_dbus_message(
                session_bus,
                MessageType.METHOD_CALL,
                "org.freedesktop.DBus",
                "org.freedesktop.DBus",
                "/org/freedesktop/DBus",
                "GetNameOwner",
                "s",
                [match_args["sender"]],
                bus=bus,
            )

            if sender_msg and sender_msg.message_type == MessageType.METHOD_RETURN:
                return sender_msg.body[0], signal_msg

            return "", signal_msg

        def check_message(task: asyncio.Task) -> None:
            new_match_args = match_args.copy()
            new_sender, signal_message = task.result()
            new_match_args["sender"] = new_sender
            if match_message(signal_message, new_match_args):
                callback(signal_message)

        def signal_callback_wrapper(msg: Message) -> None:
            """Custom wrapper to only run callback if message matches our rule."""
            if msg.message_type == MessageType.SIGNAL:
                if match_message(msg, match_args):
                    callback(msg)
                elif "sender" in match_args:
                    # If the message didn't match and we're trying to match the sender
                    # We may need to convert the pretty name to the bus's unique name first
                    task = create_task(resolve_sender(msg))
                    if task:
                        task.add_done_callback(check_message)

        bus.add_message_handler(signal_callback_wrapper)
        return True

    else:
        return False


async def find_dbus_service(service: str, session_bus: bool) -> bool:
    """Looks up service name to see if it is currently available on dbus."""

    # We're using low level interface here to reduce unnecessary calls for
    # introspection etc.
    bus, msg = await _send_dbus_message(
        session_bus,
        MessageType.METHOD_CALL,
        "org.freedesktop.DBus",
        "org.freedesktop.DBus",
        "/org/freedesktop/DBus",
        "ListNames",
        "",
        [],
    )

    if bus is None or msg is None or (msg and msg.message_type != MessageType.METHOD_RETURN):
        logger.warning("Unable to send lookup call to dbus.")
        return False

    bus.disconnect()

    names = msg.body[0]

    return service in names


def remove_dbus_rules() -> None:
    # Disconnecting the bus connections is enough to remove the match rules.
    while dbus_bus_connections:
        bus = dbus_bus_connections.pop()
        try:
            bus.disconnect()
        except OSError:
            # Socket has already shut down
            pass

        # We need to manually close the socket until https://github.com/altdesktop/python-dbus-next/pull/148
        # gets merged. There's no error on multiple calls to 'close()'.
        bus._sock.close()


def reap_zombies() -> None:
    """
    A SIGCHLD handler that reaps all zombies until there are no more.
    """
    try:
        # One signal might mean mulitple children have exited. Reap everything
        # that has exited, until there's nothing left.
        while True:
            wait_result = os.waitid(os.P_ALL, 0, os.WEXITED | os.WNOHANG)
            if wait_result is None:
                return
    except ChildProcessError:
        pass
