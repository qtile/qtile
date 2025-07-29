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
from libqtile.backend.base import zmanager
from libqtile.backend.base.window import _Window
from libqtile.backend.base.zmanager import LayerGroup, StackInfo, check_window
from libqtile.backend.x11 import window
from libqtile.log_utils import logger


class ZManager(zmanager.ZManager):
    def __init__(self, core) -> None:
        super().__init__(core)
        self.layers: dict[LayerGroup, list[_Window]] = {l: [] for l in LayerGroup}
        self.layer_map: dict[_Window, tuple(LayerGroup, int)] = {}

    def is_stacked(self, window: _Window) -> bool:
        return window in self.layer_map

    def get_layer(self, window) -> LayerGroup | None:
        layer, _ = self.layer_map.get(window, (None, 0))
        return layer

    @check_window
    def get_window_above(self, window) -> StackInfo | None:
        stack = self.get_z_order()
        idx = stack.index(window)
        if idx < (len(stack) - 1):
            sibling = stack[idx + 1]
            return StackInfo(sibling=sibling, above=True)

    @check_window
    def get_window_below(self, window) -> StackInfo | None:
        stack = self.get_z_order()
        idx = stack.index(window)
        if idx > 0:
            sibling = stack[idx - 1]
            return StackInfo(sibling=sibling, above=False)

    def add_window(self, window: _Window, layer: LayerGroup = LayerGroup.LAYOUT, position="top") -> None:
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

        window.stack(self.get_window_below(window) or self.get_window_above(window))

    @check_window
    def remove_window(self, window) -> None:
        layer, _ = self.layer_map.pop(window)
        self.layers[layer].remove(window)
        self._reindex_layer(layer)

    @check_window
    def move_up(self, window) -> StackInfo | None:
        layer, cur_idx = self.layer_map[window]
        visible = [w for w in self.layers[layer] if w.is_visible() and w.group in (window.group, None)]
        print(layer, visible)
        idx = visible.index(window)
        if idx < (len(visible) - 1):
            dest_idx =  self.layers[layer].index(visible[idx + 1])
            win = self.layers[layer].pop(cur_idx)
            self.layers[layer].insert(dest_idx, win)

        self._reindex_layer(layer)

        return self.get_window_below(window)

    @check_window
    def move_down(self, window) -> StackInfo | None:
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
    def move_to_top(self, window) -> StackInfo | None:
        layer, _ = self.layer_map[window]
        self.layers[layer].remove(window)
        self.layers[layer].append(window)
        self._reindex_layer(layer)

        return self.get_window_below(window)

    @check_window
    def move_to_bottom(self, window) -> StackInfo | None:
        layer, _ = self.layer_map[window]
        self.layers[layer].remove(window)
        self.layers[layer].insert(0, window)
        self._reindex_layer(layer)

        return self.get_window_above(window)

    @check_window
    def move_window_to_layer(self, window, new_layer, position="top") -> StackInfo | None:
        old_layer, _ = self.layer_map[window]
        if old_layer is new_layer:
            return
        self.layers[old_layer].remove(window)

        print(window, position)
        if position == "bottom":
            self.layers[new_layer].insert(0, window)
        else:
            self.layers[new_layer].append(window)

        self.layer_map[window] = (new_layer, self.layers[new_layer].index(window))
        self._reindex_layer(old_layer)
        self._reindex_layer(new_layer)

        return self.get_window_below(window) or self.get_window_above(window)

    def get_z_order(self) -> list[_Window]:
        z_order = []
        for clients in self.layers.values():
            z_order.extend(clients)
        return z_order

    def _reindex_layer(self, layer) -> None:
        for idx, win in enumerate(self.layers[layer]):
            self.layer_map[win] = (layer, idx)

    def update_client_lists(self):
        """Updates the _NET_CLIENT_LIST and _NET_CLIENT_LIST_STACKING properties

        This is needed for third party tasklists and drag and drop of tabs in
        chrome
        """
        assert self.core.qtile
        z_order = self.get_z_order()
        # Regular top-level managed windows, i.e. excluding Static, Internal and Systray Icons
        wids = [win.wid for win in z_order if isinstance(win, window.Window)]
        self.core._root.set_property("_NET_CLIENT_LIST", wids)

        self.core._root.set_property("_NET_CLIENT_LIST_STACKING", [win.wid for win in z_order])       
