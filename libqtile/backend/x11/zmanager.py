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
from functools import wraps

import xcffib.xproto

from libqtile.backend.base import LayerGroup
from libqtile.backend.x11.window import Window, _Window
from libqtile.log_utils import logger


def check_window(func):
    """
    Decorator that requires window to be stacked before proceeding.

    The decorated method must take the window's id as the first argument.
    """

    @wraps(func)
    def _wrapper(self, window, *args, **kwargs):
        if not self.is_stacked(window):
            return
        return func(self, window, *args, **kwargs)

    return _wrapper


class TreeNode:
    """
    Class to represent one node on ZManager's stacking tree.

    A node retains basic information about the layer group or client window
    it represents.

    Nodes have the ability to change their position in the tree.
    """

    def __init__(self, window=None, layer_group=None):
        self.win = window
        self.parent = None
        self.children = []
        self.layer_group = layer_group
        self.depth = 0

    def __repr__(self):
        if self.parent is None and self.layer_group is None:
            return "<ZManager Tree Root>"
        elif self.layer_group:
            return f"{' ' * self.depth * 2}<ZManager: LayerGroup.{self.layer_group.name}>"
        else:
            return f"{' ' * self.depth * 2}<ZManager: {self.win}>"

    def __iter__(self):
        yield self
        for child in self.children:
            yield from child

    @property
    def client_root(self):
        root_node = self.root_node
        node = self
        if node.parent is None:
            return None
        while node.parent is not root_node:
            node = node.parent
        return node

    @property
    def root_node(self):
        node = self
        while getattr(node.parent, "parent", None) is not None:
            node = node.parent
        return node

    @property
    def tree_root(self):
        return self.root_node.parent

    @property
    def grouped_siblings(self):
        return [
            child for child in self.parent.children if child.win.group in (None, self.win.group)
        ]

    def get_stack_order(self):
        """Return self + all descendants in stacking order (parent first)."""
        result = [self]
        for c in self.children:
            result.extend(c.get_stack_order())
        return [node for node in result if node.win]

    def stack(self):
        stack_order = self.tree_root.get_stack_order()
        index = stack_order.index(self)
        if len(stack_order) == 1:
            return

        above = index > 0
        sibling = stack_order[index - 1 if above else index + 1]

        self.win.window.configure(
            stackmode=xcffib.xproto.StackMode.Above if above else xcffib.xproto.StackMode.Below,
            sibling=sibling.win.wid,
        )

        self.stack_children()

    def stack_children(self):
        if not self.children:
            return

        parent = self.win.wid
        for child in list(self)[1:]:
            child.win.window.configure(
                stackmode=xcffib.xproto.StackMode.Above,
                sibling=parent,
            )
            parent = child.win.wid

    def get_tree(self):
        lines = []
        for node in self:
            lines.append(repr(node))
        return lines

    def add_child(self, node, position=-1):
        node.parent = self
        node.depth = node.parent.depth + 1
        if position == -1:
            self.children.append(node)
        else:
            self.children.insert(position, node)

    def remove(self):
        # If we have children windows then transfer them to
        # our parent
        if self.children:
            for child in self.children:
                self.parent.add_child(child)

        self.parent.children.remove(self)

    def get_ordered_nodes(self):
        """Return self + all descendants in stacking order (parent first)."""
        result = [self]
        for c in self.children:
            result.extend(c.all_nodes_flat())
        return result

    def move_up(self):
        """Move this node up among siblings, if possible."""
        if not self.parent:
            return  # top-level; handle differently if needed
        siblings = self.grouped_siblings
        idx = siblings.index(self)
        if idx < len(siblings) - 1:
            dest_idx = self.parent.children.index(siblings[idx + 1])
            self.parent.children.remove(self)
            self.parent.add_child(self, dest_idx)
        self.stack()

    def move_down(self):
        """Move this node down among siblings, if possible."""
        if not self.parent:
            return
        siblings = self.grouped_siblings
        idx = siblings.index(self)
        if idx > 0:
            dest_idx = self.parent.children.index(siblings[idx - 1])
            self.parent.children.remove(self)
            self.parent.add_child(self, dest_idx)
        self.stack()

    def move_to_top(self):
        if not self.parent:
            return
        self.parent.children.remove(self)
        self.parent.add_child(self)
        self.stack()

    def move_to_bottom(self):
        if not self.parent:
            return
        self.parent.children.remove(self)
        self.parent.add_child(self, 0)
        self.stack()

    def move_to_layer(self, layer):
        pass


class ZManager:
    """
    Helper class to manage stacking of windows in the X11 backend.

    The manager creates a tree of multiple layer groups. New clients are added as children
    of the appropriate layer group.

    Nesting clients allows transient windows to be attached to their parent and moved up and
    down the tree while ensuring the child is always above the parent.
    """

    def __init__(self, core) -> None:
        self.core = core
        self.layers: dict[LayerGroup, TreeNode] = {l: TreeNode(layer_group=l) for l in LayerGroup}
        self.layer_map: dict[_Window, TreeNode] = {}
        self.root = TreeNode()
        for n in self.layers.values():
            self.root.add_child(n)

    def is_stacked(self, window: _Window) -> bool:
        """Returns True if window has been added to the tree."""
        return window in self.layer_map

    def add_window(
        self, window: _Window, layer: LayerGroup = LayerGroup.LAYOUT, position="top"
    ) -> None:
        """Adds new client window to the stacking tree."""
        if layer not in self.layers:
            raise ValueError(f"Invalid layer: {layer}")

        if window in self.layer_map:
            logger.warning("Can't add existing window to zmanager.")
            return

        # Create a tree node and keep a reference to it
        node = TreeNode(window)
        self.layer_map[window] = node

        # Check if window is transient and, if so, save info
        parent = window.is_transient_for()
        if parent and parent in self.layer_map:
            # Transient windows are added as a child of their parent
            # so they are always displayed above their parent and moved
            # with them.
            self.layer_map[parent].add_child(node)

        # Not transient so stack normally.
        else:
            if position == "bottom":
                self.layers[layer].add_child(node, 0)
            else:
                self.layers[layer].add_child(node)

        # Display window in its correct location.
        node.stack()

    @check_window
    def remove_window(self, window) -> None:
        """Removes client window from the stacking tree."""
        node = self.layer_map.pop(window)
        node.remove()

    @check_window
    def replace_window(self, old_window, new_window) -> None:
        """
        Replace one window in a node with another.

        Currently only called when a window is converted to Static.
        """
        node = self.layer_map.pop(old_window)
        node.win = new_window
        self.layer_map[new_window] = node

    @check_window
    def move_up(self, window: _Window) -> None:
        """
        Move window up the tree.

        Movement is restricted to a layer group and window is
        moved relative to other visible windows.
        """
        node = self.layer_map[window]
        node.move_up()
        self.update_client_lists()

    @check_window
    def move_down(self, window) -> None:
        """
        Move window down the tree.

        Movement is restricted to a layer group and window is
        moved relative to other visible windows.
        """
        node = self.layer_map[window]
        node.move_down()
        self.update_client_lists()

    @check_window
    def move_to_top(self, window) -> None:
        """Move window to the top of its layer group."""
        node = self.layer_map[window]
        node.move_to_top()
        self.update_client_lists()

    @check_window
    def move_to_bottom(self, window) -> None:
        """Move window to the bottom of its layer group."""
        node = self.layer_map[window]
        node.move_to_bottom()
        self.update_client_lists()

    @check_window
    def move_window_to_layer(self, window, new_layer, position="top") -> None:
        """Move window to a different layer group."""
        node = self.layer_map[window]
        root = node.root_node
        root.children.remove(node)
        self.layers[new_layer].add_child(node, 0 if position == "bottom" else -1)
        node.stack()
        self.update_client_lists()

    @check_window
    def move_to_index(self, window: _Window, index: int) -> None:
        pass
        # layer, _ = self.layer_map[window]
        # self.layers[layer].remove(window)
        # self.layers[layer].insert(index, window)
        # self._reindex_layer(layer)
        # self.stack(window)

    def _restack_on_focus_change(self, window):
        """
        FULLSCREEN and BRING_TO_FRONT are temporary priority layers when window
        is focused.

        If windows lose focus they should be restacked.
        """
        for layer in (LayerGroup.FULLSCREEN, LayerGroup.BRING_TO_FRONT):
            clients = self.layers[layer]
            for client in clients:
                if client != window:
                    client.change_layer()
                    # We drop windows into the new layer after a new window has taken focus
                    # This means it will be stacked above the new window which is
                    # undesirable so we can move it below that window.
                    if self.is_above(client, window):
                        _, index = self.layer_map[window]
                        self.move_to_index(client, index)

    def update_client_lists(self):
        """
        Updates the _NET_CLIENT_LIST and _NET_CLIENT_LIST_STACKING properties

        This is needed for third party tasklists and drag and drop of tabs in
        chrome
        """
        assert self.core.qtile
        nodes = self.root.get_stack_order()
        clients = [node.win.wid for node in nodes if isinstance(node.win, Window)]
        wids = [node.win.wid for node in nodes]
        # Regular top-level managed windows, i.e. excluding Static, Internal and Systray Icons
        # wids = [win.wid for win in z_order if isinstance(win, Window)]
        self.core._root.set_property("_NET_CLIENT_LIST", clients)

        self.core._root.set_property("_NET_CLIENT_LIST_STACKING", wids)
