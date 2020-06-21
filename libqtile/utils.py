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

import functools
import importlib
import os
import sys
import traceback
import warnings
from shutil import which

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
                logger.warning(err.strerror)
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
            return fallback(module_path, class_name, error)
        raise


def safe_import(module_names, class_name, globals_, fallback=None):
    """Import a class into given globals, lazily and safely

    The globals are filled with a proxy function so that the module is imported
    only if the class is being instanciated.

    An exception is made when the documentation is being built with Sphinx, in
    which case the class is eagerly imported, for inspection.
    """
    module_path = '.'.join(module_names)
    if type(class_name) is list:
        for name in class_name:
            safe_import(module_names, name, globals_)
        return

    def class_proxy(*args, **kwargs):
        cls = import_class(module_path, class_name, fallback)
        return cls(*args, **kwargs)

    if "sphinx" in sys.modules:
        globals_[class_name] = import_class(module_path, class_name, fallback)
    else:
        globals_[class_name] = class_proxy


def send_notification(title, message, urgent=False, timeout=10000):
    """Send a notification."""
    try:
        import gi
        gi.require_version("Notify", "0.7")
        from gi.repository import Notify
        Notify.init("Qtile")
        info = Notify.get_server_info()
        if info[0]:
            notifier = Notify.Notification.new(title, message)
            notifier.set_timeout(timeout)
            if urgent:
                notifier.set_urgency(Notify.Urgency.CRITICAL)
            notifier.show()
    except Exception as exception:
        logger.error(exception)


def guess_terminal():
    """Try to guess terminal."""
    test_terminals = [
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
