import os.path
import manager


class ConfigError(Exception): pass


class File:
    def __init__(self, fname):
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
        self.commands = globs.get("commands")


