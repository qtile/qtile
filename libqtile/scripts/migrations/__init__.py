from __future__ import annotations

import importlib
import pkgutil
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from libqtile.scripts.migrations._base import _QtileMigrator

MIGRATIONS: list[type[_QtileMigrator]] = []
MIGRATION_FOLDER = Path(__file__).parent


def load_migrations():
    if MIGRATIONS:
        return
    for _, name, ispkg in pkgutil.iter_modules([MIGRATION_FOLDER.resolve().as_posix()]):
        if not name.startswith("_"):
            importlib.import_module(f"libqtile.scripts.migrations.{name}")
