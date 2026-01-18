import importlib
import inspect

from docutils.parsers.rst import Directive, directives

from libqtile.utils import import_class
from qtile_docs.base import SimpleDirectiveMixin
from qtile_docs.templates import qtile_module_template


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
