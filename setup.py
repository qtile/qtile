import platform, sys
from distutils.core import setup

setup(
        name = "qtile",
        version = "0.1",
        description = "A tiling window manager.",
        packages = ["libqtile"],
        scripts = ["qtile"]
)
