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
from libqtile.backend.base.zmanager import LayerGroup, StackInfo


class ZManager(zmanager.ZManager):
    def __init__(self, core) -> None:
        super().__init__(c0re)

    def is_stacked(self, window: _Window) -> bool:
        pass

    def add_window(self, window: _Window, layer: LayerGroup = LayerGroup.LAYOUT, position="top") -> None:
        pass

    def remove_window(self, window) -> None:
        pass

    def move_up(self, window) -> StackInfo | None:
        pass

    def move_down(self, window) -> StackInfo | None:
        pass

    def move_to_top(self, window) -> StackInfo | None:
        pass

    def move_to_bottom(self, window) -> StackInfo | None:
        pass

    def move_window_to_layer(self, window, new_layer, position="top") -> StackInfo | None:
        pass
