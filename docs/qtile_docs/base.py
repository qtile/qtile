import inspect
import pprint

from docutils import nodes
from docutils.parsers.rst import directives
from docutils.statemachine import ViewList
from sphinx.util.nodes import nested_parse_with_titles

from libqtile.command.graph import _COMMAND_GRAPH_MAP


def sphinx_escape(s):
    return pprint.pformat(s, compact=False, width=10000)


def tidy_args(method):
    """Takes a method and returns a comma separated string of the method's arguments."""
    sig = inspect.signature(method)
    args = str(sig).rsplit("(")[1].rsplit(")")[0].split(",")

    args = [f"{arg.strip()}" for arg in args[1:]]
    return ", ".join(args).replace("'", "")


def command_nodes(argument):
    """Validator for directive options. Ensures argument is a valid command graph node."""
    return directives.choice(argument, ["root"] + [node for node in _COMMAND_GRAPH_MAP])


class SimpleDirectiveMixin:
    """
    Base class for custom Sphinx directives.

    Directives inheriting this class need to define a `make_rst` method which provides a
    generator yielding individual lines of rst.
    """

    has_content = True
    required_arguments = 1

    def make_rst(self):
        raise NotImplementedError

    def run(self):
        node = nodes.section()
        node.document = self.state.document
        result = ViewList()
        for line in self.make_rst():
            result.append(line, f"<{self.__class__.__name__}>")
        nested_parse_with_titles(self.state, result, node)
        return node.children
