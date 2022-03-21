from __future__ import annotations

import json
import os.path
import re
import sys
from os import getenv
from pathlib import Path
from typing import Optional, Pattern, cast

from libqtile.backend.base import Window, WindowType
from libqtile.config import Match

if sys.version_info < (3, 8):
    from typing_extensions import TypedDict
else:
    from typing import TypedDict


class SerializedLayout(TypedDict):
    name: str


class LayoutSerDes:
    @staticmethod
    def resolve_path(name: str) -> Path:
        """resolves path to layout file
        If name consists of just one part, e.g. "my_layout" then path will resolve to ~/.config/qtile/layouts/my_layout.json
        Otherwise name is treated as a path
        """

        path = Path(name)

        if len(path.parts) == 1:
            if path.suffix != ".json":
                path = path.with_suffix(".json")

            layouts_dir = os.path.expanduser(
                os.path.join(getenv("XDG_CONFIG_HOME", "~/.config"), "qtile", "layouts")
            )

            path = Path.joinpath(Path(layouts_dir), path)
        else:
            path = path.expanduser()

        return path

    @staticmethod
    def save_to(data: SerializedLayout, name: str):
        """save this serialized layout to the specified layout file"""
        path = LayoutSerDes.resolve_path(name)
        path.parent.mkdir(parents=True, exist_ok=True)

        with path.open("w") as f:
            json.dump(data, f, indent=4)

    @staticmethod
    def load_from(name: str, check_layout_name: Optional[str] = None) -> SerializedLayout:
        """load a serialized layout from the specified layout file
        raise RuntimeError if check_layout_name is given and it does not match with value in the layout file
        """
        path = LayoutSerDes.resolve_path(name)
        with path.open() as f:
            data = json.load(f)

        if check_layout_name is not None and data["name"] != check_layout_name:
            raise RuntimeError(
                f"Loaded layout does not have expected name {check_layout_name}: {data}"
            )

        return data


class SerializedWindow(TypedDict, total=False):
    title: str
    title_regex: str
    wm_instance_class: str
    wm_instance_class_regex: str
    wm_class: str
    wm_class_regex: str
    role: str
    role_regex: str
    wm_type: str
    wm_type_regex: str
    net_wm_pid: int
    focus: bool


class WindowSerDes:
    @staticmethod
    def serialize(window: WindowType, focus: Optional[bool] = None) -> SerializedWindow:

        serialized_window = SerializedWindow(title=window.name)

        wm_role = window.get_wm_role()
        if wm_role is not None:
            serialized_window["role"] = wm_role

        wm_type = window.get_wm_type()
        if wm_type is not None:
            serialized_window["wm_type"] = wm_type

        wm_class = window.get_wm_class()
        if wm_class is not None and len(wm_class) >= 1:
            serialized_window["wm_instance_class"] = wm_class[0]

        wm_class = window.get_wm_class()
        if wm_class is not None and len(wm_class) >= 2:
            serialized_window["wm_class"] = wm_class[1]

        if isinstance(window, Window):
            serialized_window["net_wm_pid"] = cast(Window, window).get_pid()

        if focus:
            serialized_window["focus"] = True

        return serialized_window

    @staticmethod
    def _resolve_match_field_value(
        serialized_window: SerializedWindow,
        field_name: str,
        regex_field_name: str,
    ) -> Pattern | str | None:
        """looks for the _regex field. if it is None then fall back to the non _regex field"""
        if serialized_window.get(regex_field_name, None) is not None:
            return re.compile(serialized_window[regex_field_name])  # type: ignore
        else:
            return serialized_window.get(field_name, None)  # type: ignore

    @staticmethod
    def to_match(data: SerializedWindow) -> Match:
        return Match(
            title=WindowSerDes._resolve_match_field_value(data, "title", "title_regex"),
            wm_instance_class=WindowSerDes._resolve_match_field_value(
                data, "wm_instance_class", "wm_instance_class_regex"
            ),
            wm_class=WindowSerDes._resolve_match_field_value(data, "wm_class", "wm_class_regex"),
            role=WindowSerDes._resolve_match_field_value(data, "role", "role_regex"),
            wm_type=WindowSerDes._resolve_match_field_value(data, "wm_type", "wm_type_regex"),
            net_wm_pid=data.get("net_wm_pid", None),
        )
