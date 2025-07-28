# Copyright (c) 2025 elParaguayo
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
from collections import defaultdict
from enum import IntEnum
from functools import wraps

from libqtile.backend.base.window import _Window


LAYERS = ["background", "bottom", "normal", "above", "top", "overlay", "system"]

# LayerGroup = Enum("LayerGroup", {layer.name.upper(): layer.index for layer in _layers})
class LayerGroup(IntEnum):
    BACKGROUND = 0
    BOTTOM = 1
    NORMAL = 2
    ABOVE = 3
    TOP = 4
    OVERLAY = 5
    SYSTEM = 6


def check_window(func):
    """
    Decorator that requires window to be visible and stacked before proceeding.

    The decorated method must take the window's id as the first argument.
    """
    @wraps(func)
    def _wrapper(self, window, *args, **kwargs):
        if not self.is_stacked(window) or not window.is_visible():
            return
        return func(self, window, *args, **kwargs)

    return _wrapper


class ZManager:
    def __init__(self) -> None:
        self.layers: dict[LayerGroup, list[_Window]] = {l: [] for l in LayerGroup}
        self.layer_map: dict[_Window, tuple(LayerGroup, int)] = {}

    def is_stacked(self, window: _Window) -> bool:
        return window in self.layer_map

    def get_layer(self, window) -> LayerGroup | None:
        layer, _ = self.layer_map.get(window, (None, 0))
        return layer

    @check_window
    def get_window_above(self, window) -> _Window | None:
        layer, idx = self.layer_map[window]
        if idx < (len(self.layers[layer]) - 1):
            return self.layers[layer][idx + 1]

    @check_window
    def get_window_below(self, window) -> _Window | None:
        layer, idx = self.layer_map[window]
        if idx > 0:
            return self.layers[layer][idx - 1]

    def add_window(self, window: _Window, layer: LayerGroup = LayerGroup.NORMAL, position="top") -> None:
        if layer not in self.layers:
            raise ValueError(f"Invalid layer: {layer}")

        current_layer = self.get_layer(window)
        if current_layer is not None and current_layer != layer:
            logger.info("Window already stacked. Moving to new layer group.")
            self.layers[current_layer].remove(window)

        if position == "bottom":
            self.layers[layer].insert(0, window)
        else:
            self.layers[layer].append(window)

        self._reindex_layer(layer)

    @check_window
    def remove_window(self, window) -> None:
        layer, _ = self.layer_map.pop(window)
        self.layers[layer].remove(window)
        self._reindex_layer(layer)

    @check_window
    def move_up(self, window) -> _Window | None:
        layer, cur_idx = self.layer_map[window]
        visible = [w for w in self.layers[layer] if w.is_visible() and w.group in (window.group, None)]
        idx = visible.index(window)
        if idx < (len(visible) - 1):
            dest_idx =  self.layers[layer].index(visible[idx + 1])
            win = self.layers[layer].pop(cur_idx)
            self.layers[layer].insert(dest_idx, win)

        self._reindex_layer(layer)

        return self.get_window_below(window)

    @check_window
    def move_down(self, window) -> _Window | None:
        layer, cur_idx = self.layer_map[window]
        visible = [w for w in self.layers[layer] if w.is_visible() and w.group in (window.group, None)]
        idx = visible.index(window)
        if idx > 0:
            dest_idx =  self.layers[layer].index(visible[idx - 1])
            win = self.layers[layer].pop(cur_idx)
            self.layers[layer].insert(dest_idx, win)

        self._reindex_layer(layer)

        return self.get_window_above(window)

    @check_window
    def move_to_top(self, window) -> _Window | None:
        layer, _ = self.layer_map[window]
        self.layers[layer].remove(window)
        self.layers[layer].append(window)
        self._reindex_layer(layer)

        return self.get_window_below(window)

    @check_window
    def move_to_bottom(self, window) -> _Window | None:
        layer, _ = self.layer_map[window]
        self.layers[layer].remove(window)
        self.layers[layer].insert(0, window)
        self._reindex_layer(layer)

        return self.get_window_above(window)

    @check_window
    def move_window_to_layer(self, window, new_layer, position='top'):
        old_layer, _ = self.layer_map[window]
        self.layers[old_layer].remove(window)

        if position == 'bottom':
            self.layers[new_layer].insert(0, window)
        else:
            self.layers[new_layer].append(window)

        self.layer_map[window] = (new_layer, self.layers[new_layer].index(window))
        self._reindex_layer(old_layer)
        self._reindex_layer(new_layer)

        return self.get_window_below(window)

    def get_z_order(self):
        z_order = []
        for clients in self.layers.values():
            z_order.extend(clients)
        return z_order

    def _reindex_layer(self, layer):
        for idx, win in enumerate(self.layers[layer]):
            self.layer_map[win] = (layer, idx)


# Testing
class Window:
    def __init__(self, name, vis, gr):
        self.name = name
        self.vis = vis
        self.group = gr

    def is_visible(self):
        return self.vis

    def __repr__(self):
        return f"Window: <{self.name}>"

A = Window("A", True, 1)
B = Window("B", True, 2)
C = Window("C", False, 1)
D = Window("D", True, 1)

z = ZManager()

for w in (A, B, C, D):
    z.add_window(w)
