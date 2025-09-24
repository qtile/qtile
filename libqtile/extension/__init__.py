from libqtile.utils import lazify_imports

extensions = {
    "CommandSet": "command_set",
    "Dmenu": "dmenu",
    "DmenuRun": "dmenu",
    "J4DmenuDesktop": "dmenu",
    "RunCommand": "base",
    "WindowList": "window_list",
}

__all__, __dir__, __getattr__ = lazify_imports(extensions, __package__)
