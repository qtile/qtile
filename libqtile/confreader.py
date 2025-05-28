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
import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from types import FunctionType
    from typing import Any, Literal

    from libqtile.config import Group, Key, Mouse, Rule, Screen
    from libqtile.layout.base import Layout


class ConfigError(Exception):
    pass


config_pyi_header = """
from typing import Any
from typing import Literal
from libqtile.config import Group, Key, Mouse, Rule, Screen
from libqtile.layout.base import Layout

"""


class Config:
    # All configuration options
    keys: list[Key]
    mouse: list[Mouse]
    groups: list[Group]
    dgroups_key_binder: Any
    dgroups_app_rules: list[Rule]
    follow_mouse_focus: bool | Literal["click_or_drag_only"]
    focus_on_window_activation: Literal["focus", "smart", "urgent", "never"] | FunctionType
    focus_previous_on_window_remove: bool
    cursor_warp: bool
    layouts: list[Layout]
    floating_layout: Layout
    screens: list[Screen]
    auto_fullscreen: bool
    widget_defaults: dict[str, Any]
    extension_defaults: dict[str, Any]
    bring_front_click: bool | Literal["floating_only"]
    floats_kept_above: bool
    reconfigure_screens: bool
    wmname: str
    auto_minimize: bool
    # Really we'd want to check this Any is libqtile.backend.wayland.ImportConfig, but
    # doing so forces the import, creating a hard dependency for wlroots.
    wl_input_rules: dict[str, Any] | None
    wl_xcursor_theme: str | None
    wl_xcursor_size: int

    def __init__(self, file_path=None, **settings):
        """Create a Config() object from settings

        Only attributes found in Config.__annotations__ will be added to object.
        config attribute precedence is 1.) **settings 2.) self 3.) default_config
        """
        self.file_path = file_path
        self.update(**settings)

    def update(self, *, fake_screens=None, **settings):
        from libqtile.resources import default_config

        if fake_screens:
            self.fake_screens = fake_screens

        default = vars(default_config)
        for key in self.__annotations__.keys():
            try:
                value = settings[key]
            except KeyError:
                value = getattr(self, key, default[key])
            setattr(self, key, value)

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
                # and the file still exists.  If so, reload it
                if folder in subpath.parents and subpath.exists():
                    importlib.reload(module)

    def load(self):
        if not self.file_path:
            return

        path = Path(self.file_path)
        name = path.stem
        sys.path.insert(0, path.parent.as_posix())

        if name in sys.modules:
            self._reload_config_submodules(path)
            config = importlib.reload(sys.modules[name])
        else:
            config = importlib.import_module(name)

        self.update(**vars(config))

    def validate(self) -> None:
        """
        Validate the configuration against the X11 core, if it makes sense.
        """
        try:
            from libqtile.backend.x11 import core
        except ImportError:
            return

        valid_keys = core.get_keys()
        valid_mods = core.get_modifiers()
        # we explicitly do not want to set self.keys and self.mouse above,
        # because they are dynamically resolved from the default_config. so we
        # need to ignore the errors here about missing attributes.
        for k in self.keys:
            if isinstance(k.key, str) and k.key.lower() not in valid_keys:
                raise ConfigError(f"No such key: {k.key}")
            for m in k.modifiers:
                if m.lower() not in valid_mods:
                    raise ConfigError(f"No such modifier: {m}")
        for ms in self.mouse:
            for m in ms.modifiers:
                if m.lower() not in valid_mods:
                    raise ConfigError(f"No such modifier: {m}")
