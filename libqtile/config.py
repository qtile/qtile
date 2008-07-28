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
