import pytest
import xcffib
import xcffib.xfixes
import xcffib.xproto

from libqtile.backend import get_core
from libqtile.backend.x11 import core
from test.test_manager import ManagerConfig


def test_get_core_x11(display):
    get_core("x11", display).finalize()


def test_keys(display):
    assert "a" in core.get_keys()
    assert "shift" in core.get_modifiers()


def test_no_two_qtiles(xmanager):
    with pytest.raises(core.ExistingWMException):
        core.Core(xmanager.display).finalize()


def test_color_pixel(xmanager):
    xmanager.c.eval('self.core.conn.color_pixel("ffffff")')


@pytest.mark.parametrize("xmanager", [ManagerConfig], indirect=True)
def test_net_client_list(xmanager, conn):
    def assert_clients(number):
        clients = conn.default_screen.root.get_property("_NET_CLIENT_LIST", unpack=int)
        assert len(clients) == number

    # ManagerConfig has a Bar, which should not appear in _NET_CLIENT_LIST
    xmanager.c.eval("self.core.update_client_lists()")
    assert_clients(0)
    one = xmanager.test_window("one")
    assert_clients(1)
    two = xmanager.test_window("two")
    xmanager.c.window.toggle_minimize()
    three = xmanager.test_window("three")
    xmanager.c.screen.next_group()
    assert_clients(3)  # Minimized windows and windows on other groups are included
    xmanager.kill_window(one)
    xmanager.c.screen.next_group()
    assert_clients(2)
    xmanager.kill_window(three)
    assert_clients(1)
    xmanager.c.screen.next_group()
    one = xmanager.test_window("one")
    assert_clients(2)
    xmanager.c.window.static()  # Static windows are not included
    assert_clients(1)
    xmanager.kill_window(two)
    assert_clients(0)


@pytest.mark.parametrize("xmanager", [ManagerConfig], indirect=True)
def test_clear_focus_empty_group(xmanager, conn):
    """Test that _NET_ACTIVE_WINDOW is 0 when focusing an empty group"""
    xmanager.test_window("one")

    active = conn.default_screen.root.get_property("_NET_ACTIVE_WINDOW", unpack=int)
    assert active[0] != 0

    xmanager.c.screen.next_group()

    active = conn.default_screen.root.get_property("_NET_ACTIVE_WINDOW", unpack=int)
    assert active[0] == 0


class SyncSelectionsConfig(ManagerConfig):
    x11_sync_selections = True


class _SelectionClient:
    """A minimal X client that can own selections and read them back.

    Everything blocks on X events rather than polling; pytest-timeout catches
    hangs.
    """

    def __init__(self, display, selections):
        self.conn = xcffib.connect(display=display)
        self.xfixes = self.conn(xcffib.xfixes.key)
        self.xfixes.QueryVersion(xcffib.xfixes.MAJOR_VERSION, xcffib.xfixes.MINOR_VERSION)
        root = self.conn.get_setup().roots[0].root
        self.wid = self.conn.generate_id()
        self.conn.core.CreateWindow(0, self.wid, root, 0, 0, 1, 1, 0, 0, 0, 0, [])
        for selection in selections:
            self.xfixes.SelectSelectionInput(
                self.wid,
                self.atom(selection),
                xcffib.xfixes.SelectionEventMask.SetSelectionOwner,
            )
        self.contents = {}
        self.conn.flush()

    def atom(self, name):
        return self.conn.core.InternAtom(False, len(name), name).reply().atom

    def own(self, selection, value):
        self.contents[self.atom(selection)] = value
        self.conn.core.SetSelectionOwner(self.wid, self.atom(selection), 0)
        self.conn.flush()

    def owner(self, selection):
        return self.conn.core.GetSelectionOwner(self.atom(selection)).reply().owner

    def next_event(self):
        """Wait for the next event, answering any selection requests."""
        while True:
            event = self.conn.wait_for_event()
            if not isinstance(event, xcffib.xproto.SelectionRequestEvent):
                return event
            data = self.contents[event.selection].encode()
            self.conn.core.ChangeProperty(
                xcffib.xproto.PropMode.Replace, event.requestor, event.property,
                event.target, 8, len(data), data,
            )  # fmt: skip
            notify = xcffib.xproto.SelectionNotifyEvent.synthetic(
                event.time, event.requestor, event.selection, event.target, event.property
            )
            self.conn.core.SendEvent(False, event.requestor, 0, notify.pack())
            self.conn.flush()

    def wait_for_other_owner(self, selection):
        """Wait until someone other than us takes ownership of `selection`."""
        atom = self.atom(selection)
        while True:
            event = self.next_event()
            if (
                isinstance(event, xcffib.xfixes.SelectionNotifyEvent)
                and event.selection == atom
                and event.owner not in (0, self.wid)
            ):
                return

    def read(self, selection, target="UTF8_STRING"):
        prop = self.atom("QTILE_TEST_SEL")
        self.conn.core.ConvertSelection(
            self.wid, self.atom(selection), self.atom(target), prop, 0
        )
        self.conn.flush()
        while True:
            event = self.next_event()
            if isinstance(event, xcffib.xproto.SelectionNotifyEvent):
                break
        if event.property == 0:
            return None
        reply = self.conn.core.GetProperty(False, self.wid, prop, 0, 0, 2**20).reply()
        return reply.value.to_utf8()

    def close(self):
        self.conn.disconnect()


@pytest.mark.parametrize("xmanager", [SyncSelectionsConfig], indirect=True)
def test_sync_selections(xmanager):
    client = _SelectionClient(xmanager.display, ["PRIMARY", "CLIPBOARD"])
    try:
        # CLIPBOARD -> PRIMARY
        client.own("CLIPBOARD", "from the clipboard")
        client.wait_for_other_owner("PRIMARY")
        assert client.read("PRIMARY") == "from the clipboard"
        assert client.read("PRIMARY", "STRING") == "from the clipboard"
        assert client.read("PRIMARY", "IMAGE/PNG") is None

        # PRIMARY -> CLIPBOARD
        client.own("PRIMARY", "from primary ✓")
        client.wait_for_other_owner("CLIPBOARD")
        assert client.read("CLIPBOARD") == "from primary ✓"
        # we still own PRIMARY; qtile didn't fight us for it
        assert client.owner("PRIMARY") == client.wid
    finally:
        client.close()


def test_sync_selections_startup(xmanager_nospawn):
    display = xmanager_nospawn.backend.env["DISPLAY"]
    client = _SelectionClient(display, ["PRIMARY", "CLIPBOARD"])
    try:
        client.own("PRIMARY", "old primary")
        client.own("CLIPBOARD", "old clipboard")
        xmanager_nospawn.start(SyncSelectionsConfig)

        # at startup, CLIPBOARD is copied to PRIMARY and left alone itself
        client.wait_for_other_owner("PRIMARY")
        assert client.read("PRIMARY") == "old clipboard"
        assert client.owner("CLIPBOARD") == client.wid
    finally:
        client.close()
