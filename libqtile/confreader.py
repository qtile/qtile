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

import layout, bar, widget
from manager import Screen, Key, Group
from command import lazy

class ConfigError(Exception):
    pass

class Config(object):
    """ A reasonable default configuration. """

    def __init__(self):
        self.screens = [Screen(top = bar.Bar([
                widget.GroupBox(urgent_alert_method='text'),
                widget.WindowName(),
                widget.Systray(),
                widget.Clock('%Y-%m-%d %a %I:%M %p'),
            ], 30))
        ]

        mod = "mod4"

        self.keys = [
            Key(["shift", "mod1"], "q",  lazy.shutdown()),

            Key([mod], "k",              lazy.layout.down()),
            Key([mod], "j",              lazy.layout.up()),
            Key([mod], "h",              lazy.layout.previous()),
            Key([mod], "l",              lazy.layout.previous()),
            Key([mod, "shift"], "space", lazy.layout.rotate()),
            Key([mod, "shift"], "Return",lazy.layout.toggle_split()),
            Key(["mod1"], "Tab",         lazy.nextlayout()),
            Key([mod], "x",              lazy.window.kill()),

            # start specific apps
            Key([mod], "n",              lazy.spawn("firefox")),
            Key([mod], "Return",         lazy.spawn("xterm")),
        ]

        self.mouse = ()
        self.groups = []
        for i in ["a", "s", "d", "f", "u", "i", "o", "p"]:
            groups.append(Group(i))
            keys.append(
                Key([mod], i, lazy.group[i].toscreen())
            )
            keys.append(
                Key([mod, "mod1"], i, lazy.window.togroup(i))
            )

        self.layouts = [
            layout.Stack(stacks=2, border_width=1),
            layout.Max(),
        ]

        self.main = None
        self.follow_mouse_focus = True
        self.cursor_warp = False
        self.floating_layout = layout.Floating()

class File(Config):
    def __init__(self, fname=None):
        if not fname:
            config_directory = os.path.expandvars('$XDG_CONFIG_HOME')
            if config_directory == '$XDG_CONFIG_HOME': #if variable wasn't set
                config_directory = os.path.expanduser("~/.config")
            fname = os.path.join(config_directory, "qtile", "config.py")
        elif fname == "default":
            fname = utils.data.path("resources/default-config.py")

        self.fname = fname

        if not os.path.isfile(fname):
            # no config, so use the defaults above
            return
        try:
            sys.path.insert(0, os.path.dirname(self.fname))
            config = __import__(os.path.basename(self.fname)[:-3])
        except Exception, v:
            raise ConfigError(str(v))

        config_options = [
            "keys",
            "mouse",
            "groups",
            "follow_mouse_focus",
            "cursor_warp",
            "layouts",
            "floating_layout",
            "screens",
            "main",
        ]

        for option in config_options:
            if hasattr(config, option):
                setattr(self, option, getattr(config, option))

