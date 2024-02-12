from ast import AST, literal_eval

from griffe import Extension, ObjectNode, Attribute, get_logger, Module
from griffe.agents.inspector import inspect
from griffe.dataclasses import Alias
from griffe.expressions import ExprDict

logger = get_logger(__name__)


class AllWidgets(Extension):
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



class Hooks(Extension):
    def on_attribute_instance(self, *, node: AST | ObjectNode, attr: Attribute) -> None:
        if isinstance(node, ObjectNode) or attr.path != "libqtile.hook.subscribe":
            return

        # rely on dynamic analysis
        inspected_hook_module = inspect(
            "hook",
            filepath=attr.filepath,
            parent=attr.package,  # libqtile
        )

        subscribe = inspected_hook_module.get_member("subscribe")
        attr.parent.del_member("subscribe")
        attr.parent.set_member("subscribe", subscribe)