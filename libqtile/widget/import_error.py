from libqtile.widget.base import _TextBox


class ImportErrorWidget(_TextBox):
    def __init__(self, class_name, *args, **config):
        _TextBox.__init__(self, **config)
        self.text = f"Import Error: {class_name}"


def make_error(module_path, class_name):
    def import_error_wrapper(*args, **kwargs):
        return ImportErrorWidget(class_name, *args, **kwargs)

    return import_error_wrapper
