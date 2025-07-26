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
from enum import Enum


LAYERS = ["background", "bottom", "normal", "above", "top", "overlay", "system"]

class _ZLayer:
    _index = 0
    def __init__(self, name):
        self.name = name
        self.index = _ZLayer._index
        _ZLayer._index += 1
        self.clients = []

_layers = [_ZLayer(layer) for layer in LAYERS]
ZLayer = Enum("ZLayer", {layer.name.upper(): layer.index for layer in _layers})


class ZManager:
    def __init__(self):
        self.layers = _layers

    def add_window(self, window_id, layer="normal"):
        if layer not in self.layers:
            raise ValueError(f"Invalid layer: {layer}")
        self.layers[layer].append(window_id)
        self.window_lookup[window_id] = (layer, len(self.layers[layer]) - 1)

    def remove_window(self, window_id):
        layer, _ = self.window_lookup.pop(window_id)
        self.layers[layer].remove(window_id)
        self._reindex_layer(layer)

    def raise_window(self, window_id):
        layer, _ = self.window_lookup[window_id]
        self.layers[layer].remove(window_id)
        self.layers[layer].append(window_id)
        self._reindex_layer(layer)

    def lower_window(self, window_id):
        layer, _ = self.window_lookup[window_id]
        self.layers[layer].remove(window_id)
        self.layers[layer].insert(0, window_id)
        self._reindex_layer(layer)

    def move_window_to_layer(self, window_id, new_layer, position='top'):
        old_layer, _ = self.window_lookup[window_id]
        self.layers[old_layer].remove(window_id)

        if position == 'top':
            self.layers[new_layer].append(window_id)
        elif position == 'bottom':
            self.layers[new_layer].insert(0, window_id)
        else:
            self.layers[new_layer].insert(position, window_id)

        self.window_lookup[window_id] = (new_layer, self.layers[new_layer].index(window_id))
        self._reindex_layer(old_layer)
        self._reindex_layer(new_layer)

    def get_z_order(self):
        z_order = []
        for layer in self.layer_order:
            z_order.extend(self.layers[layer])
        return z_order

    def _reindex_layer(self, layer):
        for idx, win_id in enumerate(self.layers[layer]):
            self.window_lookup[win_id] = (layer, idx)
