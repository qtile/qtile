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

import functools
import glob
import importlib
import os
import traceback
import warnings
from collections import defaultdict
from collections.abc import Sequence
from random import randint
from shutil import which

from libqtile.log_utils import logger

_can_notify = False
try:
    import gi
    gi.require_version("Notify", "0.7")  # type: ignore
    from gi.repository import Notify  # type: ignore
    Notify.init("Qtile")
    _can_notify = True
except ImportError as e:
    logger.warning("Failed to import dependencies for notifications: %s" % e)


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


def rgb(x):
    """
        Returns a valid RGBA tuple.

        Here are some valid specifcations:
            #ff0000
            with alpha: #ff000080
            ff0000
            with alpha: ff0000.5
            (255, 0, 0)
            with alpha: (255, 0, 0, 0.5)
    """
    if isinstance(x, (tuple, list)):
        if len(x) == 4:
            alpha = x[3]
        else:
            alpha = 1
        return (x[0] / 255.0, x[1] / 255.0, x[2] / 255.0, alpha)
    elif isinstance(x, str):
        if x.startswith("#"):
            x = x[1:]
        if "." in x:
            x, alpha = x.split(".")
            alpha = float("0." + alpha)
        else:
            alpha = 1
        if len(x) not in (6, 8):
            raise ValueError("RGB specifier must be 6 or 8 characters long.")
        vals = [int(i, 16) for i in (x[0:2], x[2:4], x[4:6])]
        if len(x) == 8:
            alpha = int(x[6:8], 16) / 255.0
        vals.append(alpha)
        return rgb(vals)
    raise ValueError("Invalid RGB specifier.")


def hex(x):
    r, g, b, _ = rgb(x)
    return '#%02x%02x%02x' % (int(r * 255), int(g * 255), int(b * 255))


def scrub_to_utf8(text):
    if not text:
        return ""
    elif isinstance(text, str):
        return text
    else:
        return text.decode("utf-8", "ignore")


# WARNINGS
class UnixCommandNotFound(Warning):
    pass


class UnixCommandRuntimeError(Warning):
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
                logger.warning(str(err))
                warnings.warn(str(err), warning)
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
    cache_directory = os.path.join(cache_directory, 'qtile')
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
            pairs.append('%s=%s' % (attr, value))

    return ', '.join(pairs)


def import_class(module_path, class_name, fallback=None):
    """Import a class safely

    Try to import the class module, and if it fails because of an ImporError
    it logs on WARNING, and logs the traceback on DEBUG level
    """
    try:
        module = importlib.import_module(module_path, __package__)
        return getattr(module, class_name)
    except ImportError as error:
        logger.warning("Unmet dependencies for '%s.%s': %s", module_path,
                       class_name, error)
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
    if _can_notify and Notify.get_server_info()[0]:
        notifier = Notify.Notification.new(title, message)
        if urgent:
            notifier.set_urgency(Notify.Urgency.CRITICAL)
        notifier.set_timeout(timeout)
        if id is None:
            id = randint(10, 1000)
        notifier.set_property('id', id)
        notifier.show()
        return id


def guess_terminal(preference=None):
    """Try to guess terminal."""
    test_terminals = []
    if isinstance(preference, str):
        test_terminals += [preference]
    elif isinstance(preference, Sequence):
        test_terminals += list(preference)
    test_terminals += [
        'roxterm',
        'sakura',
        'hyper',
        'alacritty',
        'terminator',
        'termite',
        'gnome-terminal',
        'konsole',
        'xfce4-terminal',
        'lxterminal',
        'mate-terminal',
        'kitty',
        'yakuake',
        'tilda',
        'guake',
        'eterm',
        'st',
        'urxvt',
        'xterm',
        'x-terminal-emulator',
    ]

    for terminal in test_terminals:
        logger.debug('Guessing terminal: {}'.format(terminal))
        if not which(terminal, os.X_OK):
            continue

        logger.info('Terminal found: {}'.format(terminal))
        return terminal

    logger.error('Default terminal has not been found.')


def scan_files(dirpath, *names):
    """
    Search a folder recursively for files matching those passed as arguments, with
    globbing. Returns a dict with keys equal to entries in names, and values a list of
    matching paths. E.g.:

    >>> scan_files('/wallpapers', '*.png', '*.jpg')
    defaultdict(<class 'list'>, {'*.png': ['/wallpapers/w1.png'], '*.jpg':
    ['/wallpapers/w2.jpg', '/wallpapers/w3.jpg']})

    """
    files = defaultdict(list)

    for name in names:
        found = glob.glob(os.path.join(dirpath, '**', name), recursive=True)
        files[name].extend(found)

    return files
