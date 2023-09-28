# Copyright (c) 2008, Aldo Cortesi <aldo@corte.si>
# Copyright (c) 2011, Andrew Grigorev <andrew@ei-grad.ru>
#
# All rights reserved.
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

import importlib
import inspect
import os
import sys
import types
import typing
from functools import partial
from pathlib import Path
from typing import Any, Literal, Optional, Union

import libqtile
from libqtile.backend import get_core
from libqtile.config import Group, Key, Mouse, Rule, Screen
from libqtile.layout.base import Layout
from libqtile.log_utils import logger
from libqtile.resources import default_config


class ConfigError(Exception):
    pass


config_pyi_header = """
from typing import Any
from typing_extensions import Literal
from libqtile.config import Group, Key, Mouse, Rule, Screen
from libqtile.layout.base import Layout

"""


class Config:
    # All configuration options
    # While we support Python 3.9 we can't use the | operator in types as annotations
    # are evaluated at runtime for config validation.
    keys: list[Key]
    mouse: list[Mouse]
    groups: list[Group]
    dgroups_key_binder: Any
    dgroups_app_rules: list[Rule]
    follow_mouse_focus: bool
    focus_on_window_activation: Literal["focus", "smart", "urgent", "never"]
    cursor_warp: bool
    layouts: list[Layout]
    floating_layout: Layout
    screens: list[Screen]
    fake_screens: Optional[list[Screen]]
    auto_fullscreen: bool
    widget_defaults: dict[str, Any]
    extension_defaults: dict[str, Any]
    bring_front_click: Union[bool, Literal["floating_only"]]
    floats_kept_above: bool
    reconfigure_screens: bool
    wmname: str
    auto_minimize: bool
    # Really we'd want to check this Any is libqtile.backend.wayland.ImportConfig, but
    # doing so forces the import, creating a hard dependency for wlroots.
    wl_input_rules: Optional[dict[str, Any]]

    def __init__(self, file_path: str | None = None) -> None:
        """This stores loaded configuration values.

        Config.__annotations__ lists all possible options and their types. Default
        values are loaded from the default config at startup, and then are attempted to
        be loaded from the config (assuming the config is error-free).
        """
        if file_path:
            self.file_path: Path | None = Path(file_path)
            sys.path.insert(0, self.file_path.parent.as_posix())
        else:
            # Not specifying a path is mainly useful for tests.
            self.file_path = None

        # Load default values, which need to be kept around in case a setting is removed
        # from the user config and the default value is needed again.
        self._defaults: dict[str, Any] = {
            k: getattr(default_config, k) for k in Config.__annotations__.keys()
        }
        self.__dict__.update(self._defaults)

        # Load valid types. From 3.10 we have inspect.get_annotations.
        # See https://docs.python.org/3/howto/annotations.html
        if hasattr(inspect, "get_annotations"):
            self._types = inspect.get_annotations(Config, eval_str=True)
        else:
            self._types = {k: eval(v) for k, v in Config.__annotations__.items()}

    def _reload_config_submodules(self, path: Path) -> None:
        """Reloads python files from same folder as config file."""
        folder = path.parent
        for module in sys.modules.copy().values():
            # Skip built-ins and anything with no filepath.
            if hasattr(module, "__file__") and module.__file__ is not None:
                subpath = Path(module.__file__)

                if subpath == path:
                    # do not reevaluate config itself here, we want only
                    # reload all submodules. Also we cant reevaluate config
                    # here, because it will cache all current modules before they
                    # are reloaded. Thus, config file should be reloaded after
                    # this routine.
                    continue

                # Check if the module is in the config folder or subfolder
                # if so, reload it
                if folder in subpath.parents:
                    importlib.reload(module)

    def load(self) -> None:
        new_config = self._do_load()
        self.__dict__.update(new_config)

    def validate(self) -> None:
        self._do_load()

    def _do_load(self) -> dict[str, Any]:
        path = self.file_path

        if path is None:
            # This is a test config that doesn't load from file. Instead, config values
            # were specified as class attributes on a subclass.
            classattrs = {}
            keys = self._defaults.keys()
            # follow the parents of test classes up to Config and object.
            for cls in reversed(self.__class__.mro()[:-2]):
                attrs = vars(cls)
                classattrs.update({k: v for k, v in attrs.items() if k in keys})
            return classattrs

        name = path.stem

        try:
            if name in sys.modules:
                self._reload_config_submodules(path)
                config = importlib.reload(sys.modules[name])
            else:
                config = importlib.import_module(name)
        except Exception as e:
            raise ConfigError from e

        settings = vars(config)
        specified_keys = self._types.keys() & settings.keys()
        new_config = self._defaults.copy()

        # Values must pass type checking to be applied.
        errors = set()
        for key in specified_keys:
            valid_type = self._types[key]
            value = settings[key]

            if self._check_type(valid_type, value):
                new_config[key] = value
            else:
                errors.add(key)

        if errors:
            logger.warning("Didn't load (invalid types): %s", ", ".join(errors))

        # Check the values
        try:
            self._check_values(new_config)
        except ConfigError as e:
            # Continue anyway, but log that something didn't validate.
            logger.warning(e.args[0])

        return new_config

    def _check_type(self, valid_type: Any, value: Any) -> bool:
        """
        Perform basic run-time type checking of a value using annotations.
        """
        if origin := typing.get_origin(valid_type):
            # valid_type is parameterised, so let's check the origin and arguments
            args = typing.get_args(valid_type)

            if origin is list:
                check = partial(self._check_type, args[0])
                return all(map(check, value))

            if origin is Literal:
                return value in args

            if origin is dict:
                check_keys = partial(self._check_type, args[0])
                check_vals = partial(self._check_type, args[1])
                return all(map(check_keys, value.keys())) and all(map(check_vals, value.values()))

            if origin in (types.UnionType, typing.Union):
                return any(self._check_type(t, value) for t in args)

            # This function hasn't accounted for this type yet. Log that this happened,
            # but assume the type check would have passed.
            logger.warning("Config type checking didn't check: %s", valid_type)
            return True

        # valid_type is not parameterised, it's either Any or something we can
        # isinstance directly.
        return valid_type is Any or isinstance(value, valid_type)

    def _check_values(self, config: dict[str, Any]) -> None:
        """Try to check that the values in the config are valid."""
        if libqtile.qtile is not None:
            # First try to get the running core from the current process
            core = libqtile.qtile.core
        else:
            # Otherwise, try to import a core
            if "WAYLAND_DISPLAY" in os.environ:
                core_name = "wayland"
            else:
                core_name = "x11"
            try:
                core = get_core(core_name)
            except ImportError:
                return

        valid_keys = core.get_keys()
        valid_mods = core.get_modifiers()

        if valid_keys is not None:
            for k in self.keys:
                if k.key.lower() not in valid_keys:
                    raise ConfigError(f"No such key: {k.key}")
                for m in k.modifiers:
                    if m.lower() not in valid_mods:
                        raise ConfigError(f"No such modifier: {m}")
        if valid_mods is not None:
            for ms in self.mouse:
                for m in ms.modifiers:
                    if m.lower() not in valid_mods:
                        raise ConfigError(f"No such modifier: {m}")
