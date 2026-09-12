import xcffib.xproto

from libqtile.backend.base.stacking import _StackingManager
from libqtile.backend.x11.window import Window, XWindow


class X11StackingManager(_StackingManager):
    _root: XWindow

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
        super().restack()
        self.update_client_lists()
