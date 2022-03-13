from pathlib import Path
import json

from libqtile.log_utils import logger


class SerializedLayout:
    def __init__(self, name):
        self.data = {}
        self["name"] = name

    def __getitem__(self, key):
        return self.data[key]

    def __setitem__(self, key, value):
        self.data[key] = value

    @staticmethod
    def _resolve_path(name: str) -> Path:
        """
        If name consists of just one part, e.g. "my_layout" then path will resolve to ~/.config/qtile/layouts/my_layout.json
        Otherwise name is treated as a path
        """

        path = Path(name)

        if len(path.parts) == 1:
            if path.suffix != ".json":
                path = path.with_suffix(".json")
            path = Path.joinpath(Path("~/.config/qtile/layouts"), path).expanduser()
        else:
            path = path.expanduser()

        return path

    def save_to(self, name):
        path = self._resolve_path(name)

        path.parent.mkdir(parents=True, exist_ok=True)

        with path.open("w") as f:
            json.dump(self.data, f, indent=4)

    @classmethod
    def load_from(cls, name, check_layout_name=None):
        path = cls._resolve_path(name)

        with path.open() as f:
            data = json.load(f)

        if check_layout_name is not None and data["name"] != check_layout_name:
            logger.error(f"Loaded layout does not have expected name {check_layout_name}: {data}")
            return None

        serialized_layout = SerializedLayout(None)
        serialized_layout.data = data
        return serialized_layout


def serialize_window(window, is_focus: bool):
    wm_class = window.get_wm_class()
    if wm_class != None:
        wm_class = None if len(wm_class) == 0 else wm_class[0]

    serialized_window = {
        "wm_name": window.name,
        "wm_class": wm_class,
        "wm_role": window.get_wm_role(),
        "wm_type": window.get_wm_type(),
    }

    if is_focus:
        serialized_window["focus"] = True

    return serialized_window
