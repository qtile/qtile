'''
Copyright (c) 2008, Aldo Cortesi. All rights reserved.

 Permission is hereby granted, free of charge, to any person obtaining a copy
 of this software and associated documentation files (the "Software"), to deal
 in the Software without restriction, including without limitation the rights
 to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 copies of the Software, and to permit persons to whom the Software is
 furnished to do so, subject to the following conditions:

 The above copyright notice and this permission notice shall be included in
 all copies or substantial portions of the Software.

 THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 SOFTWARE.
'''

import os.path
import sys
import utils

class ConfigError(Exception):
    """
    Custom exception class
    """
    pass


class Config(object):
    
    """
    Base class to hold configuration data
    """
    
    keys = ()
    mouse = ()
    groups = None
    layouts = None
    screens = ()
    main = None
    follow_mouse_focus = True
    cursor_warp = False


class File(Config):

    """
    This class deals with the reading and instantiation of the
    data from the config file that has been loaded for qtile.
    """
    
    def __init__(self, fname=None):

        """
        Takes a filename for which configuration file will be
        used for the data.
        """
        
        if not fname:
            config_directory = os.path.expandvars('$XDG_CONFIG_HOME')
            if config_directory == '$XDG_CONFIG_HOME': #if variable wasn't set
                config_directory = os.path.expanduser("~/.config")
            fname = os.path.join(config_directory, "qtile", "config.py")
        elif fname == "default":
            fname = utils.data.path("resources/default-config.py")

        self.fname = fname
        globs = {}

        if not os.path.isfile(fname):
            raise ConfigError("Config file does not exist: %s"%fname)
        try:
            #to allow 'import'ing from the config dir
            sys.path.append(os.path.dirname(self.fname)) 
            execfile(self.fname, {}, globs)
        except Exception, error:
            raise ConfigError(str(error))

        # configs with defaults
        self.mouse = globs.get("mouse", [])
        self.follow_mouse_focus = globs.get("follow_mouse_focus", True)
        self.cursor_warp = globs.get("cursor_warp", False)
        self.floating_layout = globs.get('floating_layout', None)
        if self.floating_layout is None:
            from .layout import Floating
            self.floating_layout = Floating()
        self.main = globs.get("main")

        # configs without

        self.layouts = globs.get("layouts", self.default_layout())
        self.screens = globs.get("screens")
        self.groups = globs.get("groups")
        self.keys = globs.get("keys")

    def default_layout(self):

        """
        method in case no defaults were added for the layout in the config
        """
        
        from libqtile.layout import Max
        return [Max()]
