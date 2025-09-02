import sys

from setuptools import build_meta as _orig
from setuptools.build_meta import *  # noqa: F401,F403

WAYLAND_FFI_BUILD = "./libqtile/backend/wayland/cffi/build.py"


def wants_wayland(config_settings):
    if config_settings:
        for key in ["Backend", "backend"]:
            if config_settings.get(key, "").lower() == "wayland":
                return True

    return False


def build_wheel(wheel_directory, config_settings=None, metadata_directory=None):
    """If wayland backend is requested, build it!"""
    if config_settings is None:
        config_settings = {}

    wayland_requested = wants_wayland(config_settings)
    try:
        from libqtile.backend.wayland.cffi.build import ffi_compile

        ffi_compile(verbose=wayland_requested)
    except Exception as e:
        if wayland_requested:
            sys.exit(f"Wayland backend requested but backend could not be built: {e}")
        else:
            print("Wayland backend was not built.")

    # Write library paths to file, if they are specified at build time via
    # --config-settings=PANGO_PATH=...
    libs = ["PANGO", "PANGOCAIRO", "GOBJECT", "XCBCURSOR"]
    if set(libs).intersection(config_settings.keys()):
        with open("libqtile/_build_config.py", "w") as f:
            f.write("# This file is generated at build time by builder.py\n")
            for lib in ["PANGO", "PANGOCAIRO", "GOBJECT", "XCBCURSOR"]:
                p = lib + "_PATH"
                f.write(f"{p} = {config_settings.get(lib)!r}\n")

    return _orig.build_wheel(wheel_directory, config_settings, metadata_directory)
