# Copyright (c) 2015 dmpayton
# Copyright (c) 2021 elParaguayo
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
            result.append(line, "<{0}>".format(self.__class__.__name__))
        nested_parse_with_titles(self.state, result, node)
        return node.children
