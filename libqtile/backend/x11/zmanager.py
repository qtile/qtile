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
from libqtile.backend.base.zmanager import LayerGroup
from libqtile.backend.x11 import window

class ZManager(zmanager.ZManager):
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

    def add_window(self, window: _Window, layer: LayerGroup = LayerGroup.LAYOUT, position="top") -> None:
        super().add_window(window, layer, position)
        window.stack(self.get_window_below(window) or self.get_window_above(window))
