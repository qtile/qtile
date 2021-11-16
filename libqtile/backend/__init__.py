import importlib
from enum import Enum

from libqtile.utils import QtileError


class Backends(str, Enum):
    x11 = "x11"
    wayland = "wayland"


def get_core(backend, *args):
    if not hasattr(Backends, backend):
        raise QtileError(f"Backend {backend} does not exist")

    return importlib.import_module(f"libqtile.backend.{backend}.core").Core(*args)
