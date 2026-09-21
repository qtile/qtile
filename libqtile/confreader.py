from __future__ import annotations

import importlib
import sys
from collections.abc import Callable
from pathlib import Path
from types import FunctionType, ModuleType
from typing import Any, Literal

from libqtile.config import Group, IdleInhibitor, IdleTimer, Key, Mouse, Output, Rule, Screen
from libqtile.layout.base import Layout


class ConfigError(Exception):
    pass


config_pyi_header = """
from collections.abc import Callable
from typing import Any
from typing import Literal
from types import FunctionType
from libqtile.config import Group, IdleInhibitor, IdleTimer, Key, Mouse, Output, Rule, Screen
from libqtile.layout.base import Layout

"""


class Config:
    # All configuration options
    keys: list[Key]
    mouse: list[Mouse]
    groups: list[Group]
    dgroups_key_binder: Any
    dgroups_app_rules: list[Rule]
    follow_mouse_focus: bool | Literal["click_or_drag_only"]
    focus_on_window_activation: Literal["focus", "smart", "urgent", "never"] | FunctionType
    focus_previous_on_window_remove: bool
    cursor_warp: bool
    layouts: list[Layout]
    floating_layout: Layout
    screens: list[Screen]
    auto_fullscreen: bool
    widget_defaults: dict[str, Any]
    extension_defaults: dict[str, Any]
    bring_front_click: bool | Literal["floating_only"]
    floats_kept_above: bool
    reconfigure_screens: bool
    screen_change_debounce_timeout: int | float
    wmname: str
    auto_minimize: bool
    # Really we'd want to check this Any is libqtile.backend.wayland.ImportConfig, but
    # doing so forces the import, creating a hard dependency for wlroots.
    wl_input_rules: dict[str, Any] | None
    wl_xcursor_theme: str | None
    wl_xcursor_size: int
    idle_timers: list[IdleTimer]
    idle_inhibitors: list[IdleInhibitor]
    fake_screens: list[Screen] | None
    generate_screens: Callable[[list[Output]], list[Screen]] | None

    def __init__(self, file_path=None, **settings):
        """Create a Config() object from settings

        Only attributes found in Config.__annotations__ will be added to object.
        config attribute precedence is 1.) **settings 2.) self 3.) default_config
        """
        self.file_path = file_path
        self.update(**settings)

    def update(self, **settings):
        from libqtile.resources import default_config

        default = vars(default_config)
        for key in Config.__annotations__.keys():
            try:
                value = settings[key]
            except KeyError:
                if key == "screens" and (
                    settings.get("generate_screens") is not None
                    or getattr(self, "generate_screens", None) is not None
                    or settings.get("fake_screens") is not None
                    or getattr(self, "fake_screens", None) is not None
                ):
                    value = []
                else:
                    value = getattr(self, key, default.get(key, None))
            setattr(self, key, value)

    def _reload_config_submodules(self, path: Path) -> None:
        """Reload Python files imported by the config from the config folder."""
        name = path.stem
        top_module = sys.modules.get(name)
        if not isinstance(top_module, ModuleType):
            return

        folder = path.parent.resolve()
        config_file = path.resolve()
        visited: set[ModuleType] = set()
        modules_to_reload: list[ModuleType] = []

        def walk(module: ModuleType) -> None:
            if module in visited:
                return
            visited.add(module)

            candidates: list[ModuleType] = []
            for value in module.__dict__.values():
                candidate = None
                if isinstance(value, ModuleType):
                    candidate = value
                else:
                    try:
                        module_name = getattr(value, "__module__")
                    except AttributeError:
                        continue
                    candidate = sys.modules.get(module_name)

                if isinstance(candidate, ModuleType) and candidate not in visited:
                    candidates.append(candidate)

            module_name = getattr(module, "__name__", "")
            if module_name:
                prefix = module_name + "."
                candidates.extend(
                    submodule
                    for name, submodule in sys.modules.items()
                    if name.startswith(prefix)
                    and isinstance(submodule, ModuleType)
                    and submodule not in visited
                )

            for candidate in candidates:
                file = getattr(candidate, "__file__", None)
                if file is None:
                    continue
                try:
                    candidate_file = Path(file).resolve()
                except (OSError, TypeError, ValueError):
                    continue

                if folder not in candidate_file.parents or candidate_file == config_file:
                    continue
                if not candidate_file.exists():
                    continue

                walk(candidate)
                if (
                    getattr(candidate, "__spec__", None) is not None
                    and candidate not in modules_to_reload
                ):
                    modules_to_reload.append(candidate)

        walk(top_module)
        for module in modules_to_reload:
            importlib.reload(module)

    def load(self):
        if not self.file_path:
            return

        path = Path(self.file_path)
        name = path.stem
        sys.path.insert(0, path.parent.as_posix())

        if name in sys.modules:
            self._reload_config_submodules(path)
            config = importlib.reload(sys.modules[name])
        else:
            config = importlib.import_module(name)

        self.update(**vars(config))

    def validate(self) -> None:
        """
        Validate the configuration against the X11 core, if it makes sense.
        """
        try:
            from libqtile.backend.x11 import core
        except ImportError:
            return

        valid_keys = core.get_keys()
        valid_mods = core.get_modifiers()
        # we explicitly do not want to set self.keys and self.mouse above,
        # because they are dynamically resolved from the default_config. so we
        # need to ignore the errors here about missing attributes.
        for k in self.keys:
            if isinstance(k.key, str) and k.key.lower() not in valid_keys:
                raise ConfigError(f"No such key: {k.key}")
            for m in k.modifiers:
                if m.lower() not in valid_mods:
                    raise ConfigError(f"No such modifier: {m}")
        for ms in self.mouse:
            for m in ms.modifiers:
                if m.lower() not in valid_mods:
                    raise ConfigError(f"No such modifier: {m}")
