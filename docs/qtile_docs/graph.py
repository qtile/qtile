# Copyright (c) 2022 elParaguayo
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
from dataclasses import dataclass

from docutils.parsers.rst import Directive, directives
from qtile_docs.base import SimpleDirectiveMixin
from qtile_docs.templates import qtile_graph_template

from libqtile.command import graph

DISABLED_COLOUR = "Gray"


@dataclass
class Node:
    node: graph.CommandGraphNode
    x: float
    y: float
    fillcolor: str
    color: str
    url: str

    @property
    def name(self):
        return getattr(self.node, "object_type", "root")

    @property
    def children(self):
        return self.node.children

    def node_args(self, enabled=True, highlight=False, relative_url=str()):
        """Returns a dict of arguments that can be formatted for graphviz."""
        return {
            "pos": f"{self.x},{self.y}!",
            "color": self.color if enabled else DISABLED_COLOUR,
            "fillcolor": self.fillcolor if enabled else DISABLED_COLOUR,
            "href": f"{relative_url}{self.url}",
            "style": "filled",
            "label": self.name,
            "fontname": "bold" if highlight else "regular",
        }


ROOT = graph.CommandGraphRoot()


# Define our nodes with their positions, colours and link to API docs page.
NODES = [
    Node(ROOT, 0, 0, "Gray", "DarkGray", "root.html"),
    Node(graph._BarGraphNode, -1.94, -0.44, "Violet", "Purple", "bars.html"),
    Node(
        graph._CoreGraphNode,
        -1.56,
        1.24,
        "SlateBlue1",
        "SlateBlue",
        "backend.html",
    ),
    Node(
        graph._GroupGraphNode,
        1.56,
        1.24,
        "Orange",
        "OrangeRed",
        "groups.html",
    ),
    Node(
        graph._LayoutGraphNode,
        1.94,
        -0.44,
        "Gold",
        "Goldenrod",
        "layouts.html",
    ),
    Node(
        graph._ScreenGraphNode,
        0.86,
        -1.8,
        "LimeGreen",
        "DarkGreen",
        "screens.html",
    ),
    Node(
        graph._WidgetGraphNode,
        -0.86,
        -1.8,
        "LightBlue",
        "Blue",
        "widgets.html",
    ),
    Node(graph._WindowGraphNode, 0, 2, "Tomato", "Red", "windows.html"),
]


# Convenient dict to access node object via node name
NODES_MAP = {n.name: n for n in NODES}


COMMAND_MAP = {n.name: n.children for n in NODES}


# Generate a list of all routest in the map.
# Each route is a tuple of (start, end, bidirectional)
ROUTES = []
for node, children in COMMAND_MAP.items():
    for child in children:
        route = (node, child, node in COMMAND_MAP[child])
        # Check that the reverse route is not in the list already
        if (child, node, node in COMMAND_MAP[child]) not in ROUTES:
            ROUTES.append(route)


class QtileGraph(SimpleDirectiveMixin, Directive):
    required_arguments = 0
    option_spec = {
        "root": directives.unchanged,
        "api_page_root": directives.unchanged,
    }

    def make_nodes(self):
        """Generates the node definition lines."""
        node_lines = []

        for name, node in NODES_MAP.items():
            args_dict = node.node_args(
                name in self.visible_nodes,
                name == self.graph_name,
                self.options.get("api_page_root", ""),
            )
            args_string = ", ".join(f'{k}="{v}"' for k, v in args_dict.items())
            node_lines.extend([f"node [{args_string}];", f"{name};", ""])

        return node_lines

    def make_routes(self):
        """Generates the route definition lines."""
        route_lines = []
        for r in ROUTES:
            args = {}
            if r not in self.visible_routes:
                args["color"] = DISABLED_COLOUR
            if r[2]:
                args["dir"] = "both"

            line = f"{r[0]} -> {r[1]}"
            if args:
                args_string = ", ".join(f'{k}="{v}"' for k, v in args.items())
                line += f" [{args_string}]"
            line += ";"
            route_lines.append(line)

        return route_lines

    def find_linked_nodes_routes(self, node):
        """Identifies routes connected to the selected node."""
        nodes = []
        routes = []
        for r in ROUTES:
            # Our node is the starting node
            if r[0] == node:
                nodes.append(r[1])
                routes.append(r)
            # Our node is the ending node and it's a bidirectional route
            elif r[1] == node and r[2]:
                nodes.append(r[0])
                routes.append(r)

        return (nodes, routes)

    def make_rst(self):
        self.graph_name = self.options.get("root", "all")
        if self.graph_name == "all":
            self.visible_nodes = [n for n in NODES_MAP]
            self.visible_routes = ROUTES[:]
        else:
            linked_nodes, linked_routes = self.find_linked_nodes_routes(self.graph_name)
            self.visible_nodes = [self.graph_name]
            self.visible_nodes.extend(linked_nodes)
            self.visible_routes = linked_routes

        graph = []
        graph.append(f"strict digraph {self.graph_name} {{")
        graph.append('bgcolor="transparent"')
        graph.extend(self.make_nodes())
        graph.extend(self.make_routes())
        graph.append("}")

        rst = qtile_graph_template.render(graph=graph)
        for line in rst.splitlines():
            yield line
