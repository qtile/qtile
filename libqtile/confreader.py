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

from libqtile.backend.x11 import core

if TYPE_CHECKING:
    from typing import Any, Dict, List, Union

    from typing_extensions import Literal

    from libqtile.config import Group, Key, Mouse, Rule, Screen
    from libqtile.layout.base import Layout


class ConfigError(Exception):
    pass


config_pyi_header = """
from typing import Any, Dict, List, Union
from typing_extensions import Literal
from libqtile.config import Group, Key, Mouse, Rule, Screen
from libqtile.layout.base import Layout

"""


class Config:
    # All configuration options
    keys: List[Key]
    mouse: List[Mouse]
    groups: List[Group]
    dgroups_key_binder: Any
    dgroups_app_rules: List[Rule]
    follow_mouse_focus: bool
    focus_on_window_activation: Literal["focus", "smart", "urgent", "never"]
    cursor_warp: bool
    layouts: List[Layout]
    floating_layout: Layout
    screens: List[Screen]
    auto_fullscreen: bool
    widget_defaults: Dict[str, Any]
    extension_defaults: Dict[str, Any]
    bring_front_click: Union[bool, Literal["floating_only"]]
    reconfigure_screens: bool
    wmname: str
    auto_minimize: bool

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

    def load(self):
        if not self.file_path:
            return

        path = Path(self.file_path)
        name = path.stem
        sys.path.insert(0, path.parent.as_posix())

        if name in sys.modules:
            config = importlib.reload(sys.modules[name])
        else:
            config = importlib.import_module(name)

        self.update(**vars(config))

    def validate(self) -> None:
        """
        Validate the configuration against the core.
        """
        valid_keys = core.get_keys()
        valid_mods = core.get_modifiers()
        # we explicitly do not want to set self.keys and self.mouse above,
        # because they are dynamically resolved from the default_config. so we
        # need to ignore the errors here about missing attributes.
        for k in self.keys:
            if k.key not in valid_keys:
                raise ConfigError("No such key: %s" % k.key)
            for m in k.modifiers:
                if m not in valid_mods:
                    raise ConfigError("No such modifier: %s" % m)
        for ms in self.mouse:
            for m in ms.modifiers:
                if m not in valid_mods:
                    raise ConfigError("No such modifier: %s" % m)
