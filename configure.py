"""

    configure -- configuration toolkit
    ==================================

"""

from os import path
from collections import MutableMapping, Mapping
from datetime import timedelta
try:
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Loader

__all__ = ("Configuration", "ConfigurationError")

class ConfigurationError(ValueError):
    """ Configuration error"""

class Configuration(MutableMapping):
    """ Configuration object"""

    def __init__(self, struct=None, ctx=None):
        self.__struct = struct
        self.__ctx = ctx or {}

    # Iterable
    def __iter__(self):
        if self.__struct is None:
            raise ConfigurationError("unconfigured")
        return iter(self.__struct)

    # Container
    def __contains__(self, name):
        if self.__struct is None:
            raise ConfigurationError("unconfigured")
        return name in self.__struct

    # Sized
    def __len__(self):
        if self.__struct is None:
            raise ConfigurationError("unconfigured")
        return len(self.__struct)

    # Mapping
    def __getitem__(self, name):
        if self.__struct is None:
            raise ConfigurationError("unconfigured")
        data = self.__struct[name]
        if isinstance(data, dict):
            return self.__class__(data, self.__ctx)
        if isinstance(data, basestring):
            return data % self.__ctx
        return data

    # MutableMapping
    def __setitem__(self, name, value):
        if self.__struct is None:
            raise ConfigurationError("unconfigured")
        self.__struct[name] = value

    # MutableMapping
    def __delitem__(self, name):
        if self.__struct is None:
            raise ConfigurationError("unconfigured")
        self.__struct.__delitem__(name)

    def __getattr__(self, name):
        return self[name]

    def _merge(self, config):
        for k, v in config.items():
            if isinstance(v, Mapping) and k in self:
                if not isinstance(self[k], Mapping):
                    raise ConfigurationError("unresolveable conflict during merge")
                self[k]._merge(v)
            else:
                self[k] = v

    def merge(self, config):
        new = self.__class__({})
        new._merge(self)
        new._merge(config)
        return new

    def __add__(self, config):
        return self.merge(config)

    def configure(self, struct):
        if isinstance(struct, self.__class__):
            struct = struct._Config__struct
        self.__struct = struct

    def __repr__(self):
        return repr(self.__struct)

    __str__ = __repr__

    @classmethod
    def from_file(cls, filename, ctx=None):
        with open(filename, "r") as f:
            cfg = cls(load(f.read()), ctx=ctx)
        if "extends" in cfg:
            supcfg_path = path.join(path.dirname(filename), cfg.pop("extends"))
            supcfg = cls.from_file(supcfg_path)
            cfg = supcfg + cfg
        return cfg

    @classmethod
    def from_string(cls, string, ctx=None):
        return cls(load(string), ctx=ctx)

    @classmethod
    def from_dict(cls, d, ctx=None):
        return cls(d, ctx=ctx)

def _timedelta_contructor(loader, node):
    item = loader.construct_scalar(node)

    if not isinstance(item, basestring) or not item:
        raise ConfigurationError(
            "value '%s' cannot be interpreted as date range" % item)
    num, typ = item[:-1], item[-1].lower()

    if not num.isdigit():
        raise ConfigurationError(
            "value '%s' cannot be interpreted as date range" % item)

    num = int(num)

    if typ == "d":
        return timedelta(days=num)
    elif typ == "h":
        return timedelta(seconds=num * 3600)
    elif typ == "w":
        return timedelta(days=num * 7)
    elif typ == "m":
        return timedelta(seconds=num * 60)
    else:
        raise ConfigurationError(
            "value '%s' cannot be interpreted as date range" % item)

def load(stream):
    loader = Loader(stream)
    loader.add_constructor("!timedelta", _timedelta_contructor)
    try:
        return loader.get_single_data()
    finally:
        loader.dispose()