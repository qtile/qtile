import os.path
import manager, command


class ConfigError(Exception): pass


class Config:
    def commands(self):
        c = manager._BaseCommands()
        for i in self.layouts:
            c.add(i.commands)
        return c
        

class File(Config):
    def __init__(self, fname=None):
        if not fname:
            fname = os.path.join("~", ".qtile", "config.py")
            fname = os.path.expanduser(configfile)
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
