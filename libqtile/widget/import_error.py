from libqtile.widget.base import _TextBox


class ImportErrorWidget(_TextBox):
    def __init__(self, module_path, class_name, *args, **config):
        _TextBox.__init__(self, **config)
        self.text = f"Import Error: {class_name}"
        self.module_path = module_path
        self.widget_class = class_name


def make_error(module_path, class_name):
    def import_error_wrapper(*args, **kwargs):
        return ImportErrorWidget(module_path, class_name, *args, **kwargs)

    return import_error_wrapper
