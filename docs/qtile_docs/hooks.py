from docutils.parsers.rst import Directive

from libqtile.utils import import_class
from qtile_docs.base import SimpleDirectiveMixin
from qtile_docs.templates import qtile_hooks_template


class QtileHooks(SimpleDirectiveMixin, Directive):
    def make_rst(self):
        module, class_name = self.arguments[0].rsplit(".", 1)
        obj = import_class(module, class_name)
        for method in sorted(obj.hooks):
            rst = qtile_hooks_template.render(method=method)
            yield from rst.splitlines()
