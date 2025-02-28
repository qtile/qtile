from __future__ import annotations

import importlib
import importlib.util
from typing import TYPE_CHECKING

from libqtile.utils import QtileError

if TYPE_CHECKING:
    from typing import Any

    from libqtile.backend.base import Core


CORES = {
    "wayland": ("wlroots",),
    "x11": ("xcffib",),
}


def has_deps(backend: str) -> list[str]:
    """
    Check if the backend has all its dependencies installed.

    Args:
        backend: The backend to check.

    Returns:
        A list of missing dependencies. If this is empty, we can use this backend.
    """
    if backend not in CORES:
        raise QtileError(f"Backend {backend} does not exist")

    not_found = []
    for dep in CORES[backend]:
        if not importlib.util.find_spec(dep):
            not_found.append(dep)

    return not_found


def get_core(backend: str, *args: Any) -> Core:
    if backend not in CORES:
        raise QtileError(f"Backend {backend} does not exist")

    return importlib.import_module(f"libqtile.backend.{backend}.core").Core(*args)
