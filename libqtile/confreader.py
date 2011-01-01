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
import sys
import utils
from libqtile.manager import Key, Group, Screen
from libqtile.layout.base import Layout
from libqtile.layout.floating import Floating

class ConfigError(Exception): pass


class Config:
    keys = []
    mouse = []
    groups = []
    layouts = []
    screens = []
    main = None
    floating_layout = Floating()

config = Config()

__all__ = [
    'add_keys',
    'add_groups',
    'add_layouts',
    'add_screens',
    'add_main' ]

def initconfig(fname=None):
    if not fname:
        config_directory = os.path.expandvars('$XDG_CONFIG_HOME')
        if config_directory == '$XDG_CONFIG_HOME': #if variable wasn't set
            config_directory = os.path.expanduser("~/.config")
        fname = os.path.join(config_directory, "qtile", "config.py")
        
    elif fname == "default":
        fname = utils.data.path("resources/default-config.py")
    
    if not os.path.isfile(fname):
        raise ConfigError("Config file does not exist: %s"%fname)
    try:
        sys.path.append(os.path.dirname(fname))
        execfile(fname)
    except Exception, v:
        raise ConfigError(str(v))

def add_keys(keylist):
    config.keys = [ k for k in keylist if isinstance(k,Key) ]

def add_groups(grouplist):
    config.groups = [ g for g in grouplist if isinstance(g,Group) ]

def add_layouts(layoutlist):
    config.layouts = [ l for l in layoutlist if isinstance(l,Layout) ]

def add_screens(screenlist):
    config.screens = [ s for s in screenlist if isinstance(s,Screen) ]

def add_main(f):
    if callable(f):
        config.main = f
