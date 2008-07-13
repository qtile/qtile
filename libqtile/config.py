import manager

class ConfigError(Exception): pass

class File:
    def __init__(self, fname):
        self.fname = fname
        globs = {}
        try:
            execfile(self.fname, {}, globs)
        except Exception, v:
            raise ConfigError(str(v))
        self.keys = globs.get("keys")
        self.keys = globs.get("groups")
        self.layouts = globs.get("layouts")
        self.layouts = globs.get("commands")




