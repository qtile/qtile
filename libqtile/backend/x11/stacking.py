from __future__ import annotations

from enum import Enum
from functools import wraps
from typing import TYPE_CHECKING

import xcffib.xproto

from libqtile.backend.base import LayerGroup, WindowType
from libqtile.backend.x11.window import Window, XWindow
from libqtile.command.base import expose_command
from libqtile.core.manager import Qtile
from libqtile.log_utils import logger

if TYPE_CHECKING:
    from typing import Any


def check_window(func):
    """
    Decorator that requires window to be stacked before proceeding.

    The decorated method must take the window's id as the first argument.
    """

    @wraps(func)
    def _wrapper(self, window, *args, **kwargs):
        if window is None or not self.is_stacked(window):
            return
        return func(self, window, *args, **kwargs)

    return _wrapper


class NodeType(Enum):
    TREE_ROOT = "Tree root"
    LAYER_GROUP = "Layer group"
    WINDOW = "Window"


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

        # Transient relationships
        self.transient_parent = None
        self.transient_children = []

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
    def node_type(self):
        if self.parent is None and self.layer_group is None:
            return NodeType.TREE_ROOT
        elif self.layer_group is not None:
            return NodeType.LAYER_GROUP
        else:
            return NodeType.WINDOW

    @property
    def name(self):
        if self.node_type is NodeType.TREE_ROOT:
            return None
        elif self.node_type is NodeType.LAYER_GROUP:
            return self.layer_group.name
        else:
            return self.win.name

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
    def position(self):
        if self.node_type is NodeType.WINDOW:
            return self.win.x, self.win.y
        else:
            return 0, 0

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
        if self.parent is None or self.win is None:
            return []

        return [
            child for child in self.parent.children if child.win.group in (None, self.win.group)
        ]

    @property
    def layer(self):
        node = self
        while node.node_type is not NodeType.LAYER_GROUP:
            node = node.parent
        return node

    def stack_index(self):
        return self.grouped_siblings.index(self)

    def is_above(self, other):
        return self.layer.children.index(self) > other.layer.children.index(other)

    def swap_with(self, other):
        layer = self.layer

        a = layer.children.index(self)
        b = layer.children.index(other)

        layer.children[a], layer.children[b] = (
            layer.children[b],
            layer.children[a],
        )

    def get_stack_order(self):
        """Return self + all descendants in stacking order (parent first)."""
        result = [self]
        for c in self.children:
            result.extend(c.get_stack_order())
        return [node for node in result if node.win]

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
        node.depth = self.depth + 1

        if position == -1:
            self.children.append(node)
        else:
            self.children.insert(position, node)

    def remove(self):
        if self.parent:
            self.parent.children.remove(self)

        if self.transient_parent:
            self.transient_parent.transient_children.remove(self)

        for child in self.transient_children:
            child.transient_parent = None

        self.parent = None

    def get_ordered_nodes(self):
        """Return self + all descendants in stacking order (parent first)."""
        result = [self]
        for c in self.children:
            result.extend(c.all_nodes_flat())
        return result

    def move_up(self):
        siblings = self.grouped_siblings

        index = siblings.index(self)

        # Already highest in this group
        if index == len(siblings) - 1:
            return

        above = siblings[index + 1]

        # If moving above a transient child would break the relationship,
        # move the child up first.
        if above in self.transient_children:
            above.move_up()

        self.parent.children.remove(self)

        destination = self.parent.children.index(above)

        self.parent.children.insert(destination + 1, self)

    def move_down(self):

        siblings = self.grouped_siblings

        index = siblings.index(self)

        # Already lowest in this group
        if index == 0:
            return

        below = siblings[index - 1]

        # Child cannot move below its transient parent.
        # Move parent down first.
        if below is self.transient_parent:
            below.move_down()

        self.parent.children.remove(self)

        destination = self.parent.children.index(below)

        self.parent.children.insert(destination, self)

    def move_to_top(self):
        layer = self.layer

        layer.children.remove(self)
        layer.children.append(self)

        self.repair_transient_order()

    def move_to_bottom(self):

        layer = self.layer

        layer.children.remove(self)
        layer.children.insert(0, self)

        self.repair_transient_order()

    def move_to_layer(self, layer):
        old_layer = self.layer

        old_layer.children.remove(self)

        new_layer = self.tree_root.children[
            list(
                self.tree_root.children[i].layer_group
                for i in range(len(self.tree_root.children))
            ).index(layer)
        ]

        new_layer.add_child(self)

        for child in self.transient_children:
            child.move_to_layer(layer)

    def repair_transient_order(self):

        for child in self.transient_children:
            # Parent and child must share a layer
            if child.layer is not self.layer:
                child.move_to_layer(self.layer.layer_group)

            parent_group = self.grouped_siblings
            child_group = child.grouped_siblings

            if parent_group.index(self) > child_group.index(child):
                child.move_up()

            child.repair_transient_order()

    def info(self):
        x, y = self.position
        d = dict(
            name=self.name,
            x=x,
            y=y,
            type=self.node_type.value,
            wid=self.win.wid if self.win is not None else 0,
            children=[],
        )
        for child in self.children:
            d["children"].append(child.info())
        return d


class _StackingManager:
    """
    Class to manage stacking of windows in the X11 backend.

    The manager creates a tree of multiple layer groups. New clients are added as children
    of the appropriate layer group.

    Nesting clients allows transient windows to be attached to their parent and moved up and
    down the tree while ensuring the child is always above the parent.

    NB the class should not be instantiated directly. It is intended to be inherited by
    libqtile.backend.x11.core.Core
    """

    qtile: Qtile
    _root: XWindow

    def init_stacking(self) -> None:
        self.layers: dict[LayerGroup, TreeNode] = {l: TreeNode(layer_group=l) for l in LayerGroup}
        self.layer_map: dict[WindowType, TreeNode] = {}
        self.root = TreeNode()
        for n in self.layers.values():
            self.root.add_child(n)

    def is_stacked(self, window: WindowType) -> bool:
        """Returns True if window has been added to the tree."""
        return window in self.layer_map

    def add_window(
        self,
        window: WindowType,
        layer: LayerGroup | None = None,
        position="top",
    ) -> None:

        if layer is None:
            layer = window.get_layering_information()

        if layer not in self.layers:
            raise ValueError(f"Invalid layer: {layer}")

        if window in self.layer_map:
            logger.warning("Can't add existing window to stacking manager.")
            return

        node = TreeNode(window)
        self.layer_map[window] = node

        transient = window.is_transient_for()

        if transient and transient in self.layer_map:
            parent = self.layer_map[transient]

            # Child must be in parent's layer
            layer = parent.layer.layer_group

            node.transient_parent = parent
            parent.transient_children.append(node)

            parent.layer.add_child(node)

        else:
            if position == "bottom":
                self.layers[layer].add_child(node, 0)
            else:
                self.layers[layer].add_child(node)

        self.restack()

    def remove_window(self, wid) -> None:
        """Removes client window from the stacking tree."""
        window = self.qtile.windows_map.get(wid)
        if window is None or window not in self.layer_map:
            return
        node = self.layer_map.pop(window)
        node.remove()

    # @check_window
    def replace_window(self, old_window: WindowType, new_window: WindowType) -> None:
        """
        Replace one window in a node with another.

        Currently only called when a window is converted to Static.
        """
        node = self.layer_map.pop(old_window)
        node.win = new_window
        self.layer_map[new_window] = node
        self.restack()

    def repair_transients(self):
        for node in self.layer_map.values():
            if node.transient_parent is None:
                node.repair_transient_order()

    @check_window
    def move_up(self, window: WindowType) -> None:
        """
        Move window up the tree.

        Movement is restricted to a layer group and window is
        moved relative to other visible windows.
        """
        node = self.layer_map[window]
        node.move_up()
        self.restack()

    @check_window
    def move_down(self, window) -> None:
        """
        Move window down the tree.

        Movement is restricted to a layer group and window is
        moved relative to other visible windows.
        """
        node = self.layer_map[window]
        node.move_down()
        self.restack()

    @check_window
    def move_to_top(self, window) -> None:
        """Move window to the top of its layer group."""
        node = self.layer_map[window]
        node.move_to_top()
        self.restack()

    @check_window
    def move_to_bottom(self, window) -> None:
        """Move window to the bottom of its layer group."""
        node = self.layer_map[window]
        node.move_to_bottom()
        self.restack()

    @check_window
    def move_window_to_layer(self, window, new_layer, position="top") -> None:
        """Move window to a different layer group."""
        node = self.layer_map[window]
        root = node.root_node
        root.children.remove(node)
        self.layers[new_layer].add_child(node, 0 if position == "bottom" else -1)
        self.restack()

    @check_window
    def move_to_index(self, window: WindowType, index: int) -> None:
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

    def update_client_lists(self) -> None:
        """
        Updates the _NET_CLIENT_LIST and _NET_CLIENT_LIST_STACKING properties

        This is needed for third party tasklists and drag and drop of tabs in
        chrome
        """
        assert self.qtile

        # _NET_CLIENT_LIST has initial mapping order, starting with the oldest window.
        # We therefore use the order that qtile mapped these windows
        clients = [wid for wid, win in self.qtile.windows_map.items() if isinstance(win, Window)]
        self._root.set_property("_NET_CLIENT_LIST", clients)

        # _NET_CLIENT_LIST_STACKING has bottom-to-top stacking order so we use the zmanager order
        nodes = self.root.get_stack_order()
        wids = [node.win.wid for node in nodes if isinstance(node.win, Window) and node.win.group]
        self._root.set_property("_NET_CLIENT_LIST_STACKING", wids)

    def stack_all(self):
        nodes = self.root.get_stack_order()

        previous = None

        for node in nodes:
            if node.win is None:
                continue

            if previous:
                node.win.window.configure(
                    stackmode=xcffib.xproto.StackMode.Above,
                    sibling=previous.win.wid,
                )

            previous = node

    def restack(self):
        self.repair_transients()
        self.stack_all()
        self.update_client_lists()

    @expose_command
    def stacking_info(self) -> dict[str, Any]:
        return self.root.info()
