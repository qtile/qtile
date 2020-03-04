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
from typing import List  # noqa: F401

from libqtile.backend import base


class ConfigError(Exception):
    pass


class Config:
    settings_keys = [
        "keys",
        "mouse",
        "groups",
        "dgroups_key_binder",
        "dgroups_app_rules",
        "follow_mouse_focus",
        "focus_on_window_activation",
        "cursor_warp",
        "layouts",
        "floating_layout",
        "screens",
        "main",
        "auto_fullscreen",
        "widget_defaults",
        "extension_defaults",
        "bring_front_click",
        "wmname",
    ]

    def __init__(self, **settings):
        """Create a Config() object from settings

        Only attributes found in Config.settings_keys will be added to object.
        config attribute precedence is 1.) **settings 2.) self 3.) default_config
        """

        from .resources import default_config
        default = vars(default_config)
        for key in self.settings_keys:
            try:
                value = settings[key]
            except KeyError:
                value = getattr(self, key, default[key])
            setattr(self, key, value)
        self._init_fake_screens(**settings)

    def _init_fake_screens(self, **settings):
        " Initiaize fake_screens if they are set."
        try:
            value = settings['fake_screens']
            setattr(self, 'fake_screens', value)
        except KeyError:
            pass

    @classmethod
    def from_file(cls, kore: base.Core, path: str):
        "Create a Config() object from the python file located at path."
        try:
            sys.path.insert(0, os.path.dirname(path))
            config = __import__(os.path.basename(path)[:-3])  # noqa: F811
        except Exception:
            import traceback
            from .log_utils import logger
            logger.exception('Could not import config file %r', path)
            tb = traceback.format_exc()
            raise ConfigError(tb)
        cnf = cls(**vars(config))
        cnf.validate(kore)
        return cnf

    def validate(self, kore: base.Core) -> None:
        """
            Validate the configuration against the core.
        """
        valid_keys = kore.get_keys()
        valid_mods = kore.get_modifiers()
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
