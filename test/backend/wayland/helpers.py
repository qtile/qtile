def find_layer(stacking_info, layer_name=None):
    """Recursively search the nested stacking tree for the LAYER_LOCK node."""
    if layer_name is None:
        return None

    if not isinstance(stacking_info, dict):
        return None

    # Check current node
    if stacking_info.get("name") == layer_name:
        return stacking_info

    # Recurse through children
    for child in stacking_info.get("children", []):
        result = find_layer(child, layer_name)
        if result is not None:
            return result

    return None


def find_node_at_position(node, node_type, x, y, parent_x=0, parent_y=0):
    """
    Looks for a node at given position but, as tree nodes are relative,
    we need to track absolute position of child node.
    """
    if not isinstance(node, dict):
        return False

    abs_x = parent_x + node["x"]
    abs_y = parent_y + node["y"]

    if node["type"] == node_type:
        return abs_x == x and abs_y == y

    for child in node.get("children", []):
        result = find_node_at_position(
            child,
            node_type,
            x,
            y,
            abs_x,
            abs_y,
        )
        if result:
            return True

    return False


def count_node_types(node, counts=None):
    """Returns dict of the number of each node type in a given node."""
    if counts is None:
        counts = {}

    if not isinstance(node, dict):
        return counts

    # Count current node type
    node_type = node.get("type")
    if node_type:
        counts[node_type] = counts.get(node_type, 0) + 1

    # Recurse through children
    for child in node.get("children", []):
        count_node_types(child, counts)

    return counts
