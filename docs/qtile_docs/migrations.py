# Copyright (c) 2023 elParaguayo
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
from docutils.parsers.rst import Directive, directives
from qtile_docs.base import SimpleDirectiveMixin
from qtile_docs.templates import qtile_migrations_full_template, qtile_migrations_template

from libqtile.scripts.migrations import MIGRATIONS, load_migrations


class QtileMigrations(SimpleDirectiveMixin, Directive):
    """
    A custom directive that is used to display details about the
    migrations available to `qtile migrate`.
    """

    required_arguments = 0
    option_spec = {
        "summary": directives.flag,
        "help": directives.flag,
    }

    def make_rst(self):
        load_migrations()

        context = {"migrations": [(m, len(m.ID)) for m in MIGRATIONS]}

        if "summary" in self.options:
            rst = qtile_migrations_template.render(**context)
        elif "help" in self.options:
            rst = qtile_migrations_full_template.render(**context)

        for line in rst.splitlines():
            yield line
