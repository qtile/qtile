from ast import AST, literal_eval
import inspect
import re

from griffe import Docstring, Extension, Function, ObjectNode, Attribute, dynamic_import, get_logger, Module
from griffe.dataclasses import Alias
from griffe.expressions import ExprDict
from griffe import Extension, ObjectNode, Attribute, get_logger

logger = get_logger(__name__)


class AllWidgets(Extension):
    _re_widget_path = re.compile(r"libqtile\.widget\.\w+.\w+")

    def on_attribute_instance(self, *, node: AST | ObjectNode, attr: Attribute) -> None:
        if isinstance(node, ObjectNode):
            return
        if attr.path == "libqtile.widget.widgets":
            dict_expr: ExprDict = attr.value  # type: ignore[assignment]
            widget_module: Module = attr.parent  # type: ignore[assignment]
            widget_module.exports = list(widget_module.exports or [])
            # Alias all lazily-imported widgets, mark them as exported.
            for key, value in zip(dict_expr.keys, dict_expr.values):
                name = literal_eval(str(key))
                module = literal_eval(str(value))
                widget_module.set_member(str(name), Alias(str(name), f"libqtile.widget.{module}.{name}"))
                widget_module.exports.append(name)

    def on_function_instance(self, *, node: AST | ObjectNode, func: Function) -> None:
        if any(dec.callable_path == "libqtile.command.base.expose_command" for dec in func.decorators):
            func.labels.add("command")

    # def on_package_loaded(self, *, pkg: Module) -> None:
    #     if pkg.name != "libqtile":
    #         return
    #     for member in pkg["widget"].members.values():
    #         if member.is_alias and self._re_widget_path.match(member.target_path):
    #             widget = member.final_target
    #             commands = widget.extra["qtile"]["commands"] = []
    #             for function in widget.functions.values():
    #                 if any(dec.value.canonical_path == "libqtile.command.base.expose_command" for dec in function.decorators):
    #                     commands.append(function)


class Hooks(Extension):
    def on_module_members(self, *, node: AST | ObjectNode, mod: Module) -> None:
        if mod.path != "libqtile.hook":
            return

        subscribe = mod.get_member("subscribe")
        unsubscribe = mod.get_member("unsubscribe")

        if isinstance(node, ObjectNode):
            hooks = node.obj.hooks
        else:
            hooks = dynamic_import("libqtile.hook.hooks")

        for hook in hooks:
            docstring = Docstring(hook.doc)
            subscribe.set_member(hook.name, Function(hook.name, docstring=docstring, lineno=0, endlineno=0))
            unsubscribe.set_member(hook.name, Function(hook.name, docstring=docstring, lineno=0, endlineno=0))
