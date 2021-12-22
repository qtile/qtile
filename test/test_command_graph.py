import pytest

from libqtile.command.graph import CommandGraphCall, CommandGraphObject, CommandGraphRoot


def test_root_path():
    node = CommandGraphRoot()
    assert node.selectors == []
    assert node.selector is None
    assert node.parent is None


def test_resolve_nodes():
    root_node = CommandGraphRoot()

    node_1 = root_node.navigate("layout", None).navigate("screen", None)
    assert node_1.selectors == [("layout", None), ("screen", None)]
    assert isinstance(node_1, CommandGraphObject)

    node_2 = node_1.navigate("layout", None).navigate("window", None).navigate("group", None)
    assert node_2.selectors == [
        ("layout", None),
        ("screen", None),
        ("layout", None),
        ("window", None),
        ("group", None),
    ]
    assert isinstance(node_2, CommandGraphObject)

    with pytest.raises(KeyError, match="Given node is not an object"):
        node_1.navigate("root", None)


def test_resolve_selections():
    root_node = CommandGraphRoot()

    node_1 = root_node.navigate("layout", None).navigate("screen", "1")
    assert node_1.selectors == [("layout", None), ("screen", "1")]
    assert isinstance(node_1, CommandGraphObject)


def test_resolve_command():
    root_node = CommandGraphRoot()

    command_1 = root_node.call("cmd_name")
    assert command_1.selectors == []
    assert command_1.name == "cmd_name"
    assert isinstance(command_1, CommandGraphCall)

    command_2 = root_node.navigate("layout", None).navigate("screen", None).call("cmd_name")
    assert command_2.name == "cmd_name"
    assert command_2.selectors == [("layout", None), ("screen", None)]
    assert isinstance(command_2, CommandGraphCall)
