# coding: utf-8
#
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
import os
import sys

from libqtile.backend.x11 import core


class ConfigError(Exception):
    pass


config_pyi_header = """
from typing import Any, Dict, List, Literal
from libqtile.config import Group, Key, Mouse, Rule, Screen
from libqtile.layout.base import Layout

"""


class Config:
    settings_keys = [
        ("keys", "List[Key]"),
        ("mouse", "List[Mouse]"),
        ("groups", "List[Group]"),
        ("dgroups_key_binder", "Any"),
        ("dgroups_app_rules", "List[Rule]"),
        ("follow_mouse_focus", "bool"),
        ("focus_on_window_activation", 'Literal["focus", "smart", "urgent", "never"]'),
        ("cursor_warp", "bool"),
        ("layouts", "List[Layout]"),
        ("floating_layout", "Layout"),
        ("screens", "List[Screen]"),
        ("main", "Any"),
        ("auto_fullscreen", "bool"),
        ("widget_defaults", "Dict[str, Any]"),
        ("extension_defaults", "Dict[str, Any]"),
        ("bring_front_click", "bool"),
        ("wmname", "str"),
    ]

    def __init__(self, file_path=None, **settings):
        """Create a Config() object from settings

        Only attributes found in Config.settings_keys will be added to object.
        config attribute precedence is 1.) **settings 2.) self 3.) default_config
        """
        self.file_path = file_path
        self.update(**settings)

    def update(self, *, fake_screens=None, **settings):
        from libqtile.resources import default_config

        if fake_screens:
            self.fake_screens = fake_screens

        default = vars(default_config)
        for (key, _) in self.settings_keys:
            try:
                value = settings[key]
            except KeyError:
                value = getattr(self, key, default[key])
            setattr(self, key, value)

    def load(self):
        if not self.file_path:
            return

        name = os.path.splitext(os.path.basename(self.file_path))[0]

        # Make sure we'll import the latest version of the config
        try:
            del sys.modules[name]
        except KeyError:
            pass

        try:
            sys.path.insert(0, os.path.dirname(self.file_path))
            config = __import__(name)  # noqa: F811
        except Exception:
            import traceback

            from libqtile.log_utils import logger
            logger.exception('Could not import config file %r', self.file_path)
            tb = traceback.format_exc()
            raise ConfigError(tb)

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
        for k in self.keys:  # type: ignore
            if k.key not in valid_keys:
                raise ConfigError("No such key: %s" % k.key)
            for m in k.modifiers:
                if m not in valid_mods:
                    raise ConfigError("No such modifier: %s" % m)
        for ms in self.mouse:  # type: ignore
            for m in ms.modifiers:
                if m not in valid_mods:
                    raise ConfigError("No such modifier: %s" % m)
