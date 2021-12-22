import importlib

from libqtile.utils import QtileError

CORES = [
    "wayland",
    "x11",
]


def get_core(backend, *args):
    if backend not in CORES:
        raise QtileError(f"Backend {backend} does not exist")

    return importlib.import_module(f"libqtile.backend.{backend}.core").Core(*args)
