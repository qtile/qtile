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
import manager, command


class ConfigError(Exception): pass


class Config:
    keys = ()
    groups = None
    layouts = None
    screens = ()
    def commands(self):
        c = manager._BaseCommands()
        for i in self.layouts:
            c.update(i.commands)
        for i in self.screens:
            for b in i.gaps:
                c.update(b.commands)
                if hasattr(b, "widgets"):
                    for w in b.widgets:
                        c.update(w.commands)
        return c
        

class File(Config):
    def __init__(self, fname=None):
        if not fname:
            fname = os.path.join("~", ".qtile", "config.py")
            fname = os.path.expanduser(fname)
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
