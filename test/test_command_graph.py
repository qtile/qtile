import pytest

from libqtile.command_graph import CommandGraphCall, CommandGraphContainer, CommandGraphRoot


def test_root_path():
    node = CommandGraphRoot()
    assert node.path == ""

    assert node.selector is None
    assert node.parent is None


def test_resolve_nodes():
    root_node = CommandGraphRoot()

    node_1 = root_node.navigate("layout", None) \
                      .navigate("screen", None)
    assert node_1.path == "layout.screen"
    assert isinstance(node_1, CommandGraphContainer)

    node_2 = node_1.navigate("layout", None) \
                   .navigate("window", None) \
                   .navigate("group", None)
    assert node_2.path == "layout.screen.layout.window.group"
    assert isinstance(node_2, CommandGraphContainer)


def test_resolve_selections():
    root_node = CommandGraphRoot()

    node_1 = root_node.navigate("layout", None) \
                      .navigate("screen", "1")
    assert node_1.path == "layout.screen[1]"
    assert isinstance(node_1, CommandGraphContainer)


def test_resolve_command():
    root_node = CommandGraphRoot()

    command_1 = root_node.navigate("cmd_name", None)
    assert command_1.path == "cmd_name"
    assert command_1.name == "cmd_name"
    assert isinstance(command_1, CommandGraphCall)

    command_2 = root_node.navigate("layout", None) \
                         .navigate("screen", None) \
                         .navigate("cmd_name", None)
    assert command_2.path == "layout.screen.cmd_name"
    assert command_2.name == "cmd_name"
    assert isinstance(command_2, CommandGraphCall)

    with pytest.raises(KeyError, match="Given node is not an object"):
        root_node.navigate("cmd_name", "1")
