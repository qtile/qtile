import ast
import importlib
import importlib.util

from libqtile.log_utils import logger
from libqtile.widget.base import _TextBox


def missing_imports_from_file(file_path):
    missing = set()

    with open(file_path) as f:
        source = f.read()

    tree = ast.parse(source, filename=file_path)

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for name in node.names:
                module = name.name
                root = module.split(".")[0]

                try:
                    importlib.import_module(root)
                except ImportError:
                    missing.add(root)

        elif isinstance(node, ast.ImportFrom):
            module = node.module
            if not module:
                continue

            root = module.split(".")[0]

            try:
                importlib.import_module(root)
            except ImportError:
                missing.add(root)

    return missing


def find_missing_widget_dependencies(module_path):
    spec = importlib.util.find_spec(module_path)
    if not spec or not spec.origin:
        return []

    missing = missing_imports_from_file(spec.origin)

    return sorted(missing)


class ImportErrorWidget(_TextBox):
    registry: dict[str, list[str]] = {}

    def __init__(self, module_path, class_name, *args, **config):
        _TextBox.__init__(self, **config)
        self.text = f"Import Error: {class_name}"
        self.module_path = module_path
        self.widget_class = class_name
        self.missing_dependencies = find_missing_widget_dependencies(module_path)

        spec = f"{module_path}.{class_name}"
        if spec not in ImportErrorWidget.registry:
            logger.error(
                "%s has missing dependencies: %s.",
                class_name,
                ", ".join(self.missing_dependencies),
            )

    def info(self):
        inf = super().info()
        inf["missing_dependencies"] = self.missing_dependencies
        return inf


def make_error(module_path, class_name):
    def import_error_wrapper(*args, **kwargs):
        return ImportErrorWidget(module_path, class_name, *args, **kwargs)

    return import_error_wrapper
