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

import os.path


class ConfigError(Exception): pass


class Config:
    keys = ()
    groups = None
    layouts = None
    screens = ()
    theme = None


class File(Config):
    def __init__(self, fname=None):
        if not fname:
            config_directory = os.path.expandvars('$XDG_CONFIG_HOME')
            if config_directory == '$XDG_CONFIG_HOME': #if variable wasn't set
                config_directory = os.path.expanduser("~/.config")
            fname = os.path.join(config_directory, "qtile", "config.py")
        self.fname = fname
        globs = {}
        if not os.path.isfile(fname):
            raise ConfigError("Config file does not exist: %s"%fname)
        try:
            execfile(self.fname, {}, globs)
        except Exception, v:
            raise ConfigError(str(v))
        self.keys = globs.get("keys")
        self.groups = globs.get("groups")
        self.layouts = globs.get("layouts")
        self.screens = globs.get("screens")
        self.theme = globs.get("theme")
        if globs.get("themedir"):
            self.themedir = globs.get("themedir")
        else:
            self.themedir = os.path.join(os.path.split(self.fname)[0], "themes")

