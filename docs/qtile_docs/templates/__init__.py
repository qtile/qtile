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
from qtile_docs.templates.command import qtile_commands_template  # noqa: F401
from qtile_docs.templates.graph import qtile_graph_template  # noqa: F401
from qtile_docs.templates.hook import qtile_hooks_template  # noqa: F401
from qtile_docs.templates.migrations import (  # noqa: F401
    qtile_migrations_full_template,
    qtile_migrations_template,
)
from qtile_docs.templates.module import qtile_module_template  # noqa: F401
from qtile_docs.templates.qtile_class import qtile_class_template  # noqa: F401

__all__ = [
    "qtile_commands_template",
    "qtile_graph_template",
    "qtile_hooks_template",
    "qtile_module_template",
    "qtile_class_template",
    "qtile_migrations_template",
    "qtile_migrations_full_template",
]
