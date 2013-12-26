#!/usr/bin/env python
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
import utils
import traceback


class ConfigError(Exception):
    pass


class File(object):
    def __init__(self, fname=None, is_restart=False):
        if not fname:
            config_directory = os.path.expandvars('$XDG_CONFIG_HOME')
            if config_directory == '$XDG_CONFIG_HOME':
                # if variable wasn't set
                config_directory = os.path.expanduser("~/.config")
            fname = os.path.join(config_directory, "qtile", "config.py")
        elif fname == "default":
            fname = utils.data.path("resources/default_config.py")

        self.fname = fname

        if os.path.isfile(fname):
            try:
                sys.path.insert(0, os.path.dirname(self.fname))
                config = __import__(os.path.basename(self.fname)[:-3])
            except Exception, v:
                # On restart, user potentially has some windows open, but they
                # screwed up their config. So as not to lose their apps, we
                # just load the default config here.
                if is_restart:
                    traceback.print_exc()
                    config = None
                else:
                    tb = traceback.format_exc()
                    raise ConfigError(str(v) + "\n\n" + tb)
        else:
            config = None

        # if you add something here, be sure to add a reasonable default value
        # to resources/default_config.py
        config_options = [
            "keys",
            "mouse",
            "groups",
            "dgroups_key_binder",
            "dgroups_app_rules",
            "follow_mouse_focus",
            "cursor_warp",
            "layouts",
            "floating_layout",
            "screens",
            "main",
            "auto_fullscreen",
            "widget_defaults",
            "bring_front_click",
        ]

        # We delay importing here to avoid a circular import issue when
        # testing.
        from resources import default_config
        for option in config_options:
            if hasattr(config, option):
                v = getattr(config, option)
            else:
                v = getattr(default_config, option)
            if not hasattr(self, option):
                setattr(self, option, v)
