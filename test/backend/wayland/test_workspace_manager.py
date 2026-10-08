import pytest

from libqtile.config import Group, ScratchPad
from test.conftest import dualmonitor
from test.helpers import BareConfig


class WorkspaceManagerConfig(BareConfig):
    groups = [Group(name) for name in "abcd"]
    groups.extend(
        [
            Group("e", label=""),  # Empty label means group is hidden
            ScratchPad("f"),  # scratchpads are also hidden
        ]
    )


pytestmark = [
    pytest.mark.parametrize("test_client", ["workspace-manager"], indirect=True),
    pytest.mark.parametrize("wmanager", [WorkspaceManagerConfig], indirect=True),
]


def make_line(name, label=None, active=False, hidden=False, urgent=False):
    def yn(value):
        return "YES" if value else "no"

    return (
        f"""Workspace [{name}] "{name if label is None else label}" """
        f"(active={yn(active)}, hidden={yn(hidden)}, urgent={yn(urgent)})"
    )


def get_window(title, wmanager):
    wins = wmanager.c.windows()
    for w in wins:
        if w["name"] == title:
            return wmanager.c.window[w["id"]]

    assert False


# Test server side code


def test_workspace_group_capabilities(wmanager, test_client):
    """Test that qtile advertises ability for clients to create workspaces."""
    lines = test_client.send_read_ok("workspace_group_capabilities 0")  # index of workspace group
    assert len(lines) == 1
    assert lines[0] == "create_workspace"


def test_workspace_capabilities(wmanager, test_client):
    """Test that workspaces advertise ability to activate and remove them."""
    lines = test_client.send_read_ok("workspace_capabilities a")  # workspace name
    assert len(lines) == 2
    assert "activate" in lines
    assert "remove" in lines


def test_workspaces_active_state(wmanager, test_client):
    """Tests that all groups are passed to clients and display active state."""
    lines = test_client.send_read_ok("list")
    assert len(lines) == 5  # Scratchpads are not added
    assert make_line("a", active=True) in lines
    for group in "bcd":
        assert make_line(group) in lines

    # Change group and check that workspaces are updated
    wmanager.c.group["b"].toscreen()
    lines = test_client.send_read_ok("list")
    assert make_line("b", active=True) in lines
    for group in "acd":
        assert make_line(group) in lines


@dualmonitor
def test_workspaces_multimonitor_active_state(wmanager, test_client):
    lines = test_client.send_read_ok("list")
    assert len(lines) == 5  # Scratchpads are not added
    for group in "ab":
        assert make_line(group, active=True) in lines
    for group in "cd":
        assert make_line(group) in lines

    # Change group and check that workspaces are updated
    wmanager.c.group["c"].toscreen(0)
    wmanager.c.group["d"].toscreen(1)
    lines = test_client.send_read_ok("list")
    for group in "ab":
        assert make_line(group) in lines
    for group in "cd":
        assert make_line(group, active=True) in lines


def test_workspaces_hidden_state(wmanager, test_client):
    """Test that a group with an empty label is hidden."""
    lines = test_client.send_read_ok("list")
    assert len(lines) == 5  # Scratchpads are not added
    assert make_line("e", label="", hidden=True) in lines


def test_workspaces_urgent_state(wmanager, test_client):
    """Test that a group with an urgent window is marked accordingly."""

    # Create a window on a different group
    wmanager.c.group["b"].toscreen()
    wmanager.test_window("urgent_window")
    wmanager.c.group["a"].toscreen()

    # Check state is showing as not urgent
    lines = test_client.send_read_ok("list")
    assert make_line("b") in lines

    # Set window as urgent and verify state is updated
    win = get_window("urgent_window", wmanager)
    win.eval("self.urgent=True")
    lines = test_client.send_read_ok("list")
    assert make_line("b", urgent=True) in lines

    # Change group (tp focus urgent window) and check urgent state is removed
    wmanager.c.group["b"].toscreen()
    wmanager.c.group["a"].toscreen()
    lines = test_client.send_read_ok("list")
    assert make_line("b") in lines


@dualmonitor
def test_workspaces_outputs(wmanager, test_client):
    """Tests that qtile's workspace group is advertised on all outputs."""
    lines = test_client.send_read_ok("workspace_group_outputs 0")
    assert lines
    assert lines[0] == "outputs: 2"

    # Remove an output and confirm client is notified
    wmanager.c.core.test_destroy_output(1)
    lines = test_client.send_read_ok("workspace_group_outputs 0")
    assert lines
    assert lines[0] == "outputs: 1"


def test_workspaces_outputs_label_change(wmanager, test_client):
    """Tests whether label changes are sent to clients."""
    lines = test_client.send_read_ok("list")
    assert make_line("a", active=True) in lines
    assert make_line("b") in lines

    # Change label for group a
    wmanager.c.group["a"].set_label("test_group_a")
    lines = test_client.send_read_ok("list")
    assert make_line("a", label="test_group_a", active=True) in lines

    # Change label to empty string which causes group to be hidden
    wmanager.c.group["b"].set_label("")
    lines = test_client.send_read_ok("list")
    assert make_line("b", label="", hidden=True) in lines


def test_workspace_add_remove_workspace(wmanager, test_client):
    """Tests whether groups added/removed by qtile are sent to clients."""
    lines = test_client.send_read_ok("list")
    assert len(lines) == 5

    # Add a new group
    wmanager.c.addgroup("new_group", label="new_label")
    lines = test_client.send_read_ok("list")
    assert len(lines) == 6
    assert make_line("new_group", label="new_label") in lines

    # Delete a group
    assert make_line("b") in lines
    wmanager.c.delgroup("b")
    lines = test_client.send_read_ok("list")
    assert len(lines) == 5
    assert make_line("b") not in lines


# Test commands sent by clients


def test_workspace_client_activate_workspace(wmanager, test_client):
    """Test clients can activate workspaces."""
    assert wmanager.c.group.info()["name"] == "a"

    # Client requests group b
    test_client.assert_ok("activate b")
    assert wmanager.c.group.info()["name"] == "b"

    # Check status is also updated
    lines = test_client.send_read_ok("list")
    assert make_line("a") in lines
    assert make_line("b", active=True) in lines


@dualmonitor
def test_workspace_client_activate_workspace_multimonitor(wmanager, test_client):
    """Test clients can activate workspaces."""
    assert wmanager.c.screen[0].group.info()["name"] == "a"
    assert wmanager.c.screen[1].group.info()["name"] == "b"

    # Client requests group b
    test_client.assert_ok("activate c")
    assert wmanager.c.screen[0].group.info()["name"] == "c"

    wmanager.c.to_screen(1)
    test_client.assert_ok("activate d")
    assert wmanager.c.screen[1].group.info()["name"] == "d"

    # Check status is also updated
    lines = test_client.send_read_ok("list")
    for group in "ab":
        assert make_line(group) in lines
    for group in "cd":
        assert make_line(group, active=True) in lines


def test_workspace_client_add_remove_workspace(wmanager, test_client):
    """Test clients can create and remove workspaces."""
    test_client.assert_ok("create_workspace client_group")
    lines = test_client.send_read_ok("list")
    assert "client_group" in wmanager.c.get_groups()
    assert len(lines) == 6
    assert make_line("client_group") in lines

    assert "c" in wmanager.c.get_groups()
    test_client.assert_ok("remove c")
    assert "c" not in wmanager.c.get_groups()
    lines = test_client.send_read_ok("list")
    assert len(lines) == 5
    assert make_line("c") not in lines
