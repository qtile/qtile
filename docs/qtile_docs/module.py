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
import importlib
import inspect

from docutils.parsers.rst import Directive, directives
from qtile_docs.base import SimpleDirectiveMixin
from qtile_docs.templates import qtile_module_template

from libqtile.utils import import_class


class QtileModule(SimpleDirectiveMixin, Directive):
    optional_arguments = 3

    option_spec = {
        "baseclass": directives.unchanged,
        "no-config": directives.flag,
        "no-commands": directives.flag,
        # Comma separated list of object names to skip
        "exclude": directives.unchanged,
    }

    def make_rst(self):
        module = importlib.import_module(self.arguments[0])

        baseclass = None
        if "baseclass" in self.options:
            baseclass = import_class(*self.options["baseclass"].rsplit(".", 1))

        for item in dir(module):
            if item in self.options.get("exclude", "").split(","):
                continue
            obj = import_class(self.arguments[0], item)
            if not inspect.isclass(obj) or (baseclass and not issubclass(obj, baseclass)):
                continue

            context = {
                "module": self.arguments[0],
                "class_name": item,
                "no_config": "no-config" in self.options,
                "no_commands": "no-commands" in self.options,
            }
            rst = qtile_module_template.render(**context)
            for line in rst.splitlines():
                if not line.strip():
                    continue
                yield line
