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
from docutils import nodes
from docutils.parsers.rst import Directive, directives
from sphinx.util.nodes import nested_parse_with_titles


class CollapsibleNode(nodes.Body, nodes.Element):
    def __init__(self, source, summary, *args, **kwargs):
        self.summary = summary
        super().__init__(source, *args, **kwargs)


def visit_collapsible_node(self, node):
    self.body.append("<details>\n")
    if node.summary:
        self.body.append(f"<summary>{node.summary}</summary>\n")


def depart_collapsible_node(self, node):
    self.body.append("</details>\n")


class CollapsibleSection(Directive):
    option_spec = {
        "summary": directives.unchanged,
    }
    has_content = True

    def run(self):
        summary = self.options.get("summary", "")
        node = CollapsibleNode("\n".join(self.content), summary)
        nested_parse_with_titles(self.state, self.content, node)

        return [node]
