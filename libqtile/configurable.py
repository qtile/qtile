import copy


class Configurable:
    global_defaults = {}  # type: dict

    def __init__(self, **config):
        self._variable_defaults = {}
        self._user_config = config

    def add_defaults(self, defaults):
        """Add defaults to this object, overwriting any which already exist"""
        # Since we can't check for immutability reliably, shallow copy the
        # value. If a mutable value were set and it were changed in one place
        # it would affect all other instances, since this is typically called
        # on __init__
        self._variable_defaults.update((d[0], copy.copy(d[1])) for d in defaults)

    def __getattr__(self, name):
        if name == "_variable_defaults":
            raise AttributeError
        found, value = self._find_default(name)
        if found:
            setattr(self, name, value)
            return value
        else:
            cname = self.__class__.__name__
            raise AttributeError(f"{cname} has no attribute: {name}")

    def _find_default(self, name):
        """Returns a tuple (found, value)"""
        defaults = self._variable_defaults.copy()
        defaults.update(self.global_defaults)
        defaults.update(self._user_config)
        if name in defaults:
            return (True, defaults[name])
        else:
            return (False, None)


class ExtraFallback:
    """Adds another layer of fallback to attributes

    Used to look up a different attribute name
    """

    def __init__(self, name, fallback):
        self.name = name
        self.hidden_attribute = "_" + name
        self.fallback = fallback

    def __get__(self, instance, owner=None):
        retval = getattr(instance, self.hidden_attribute, None)

        if retval is None:
            _found, retval = Configurable._find_default(instance, self.name)

        if retval is None:
            retval = getattr(instance, self.fallback, None)

        return retval

    def __set__(self, instance, value):
        """Set own value to a hidden attribute of the object"""
        setattr(instance, self.hidden_attribute, value)
