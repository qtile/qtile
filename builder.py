import sys

from setuptools import build_meta as _orig
from setuptools.build_meta import *  # noqa: F401,F403

WAYLAND_FFI_BUILD = "./libqtile/backend/wayland/cffi/build.py"


def wants_wayland(config_settings):
    if config_settings:
        for key in ["Backend", "backend"]:
            value = config_settings.get(key, "").lower()
            if value == "wayland":
                return True
            if value == "x11":
                return False

    return None


def build_wheel(wheel_directory, config_settings=None, metadata_directory=None):
    """If wayland backend is requested, build it!"""
    if config_settings is None:
        config_settings = {}

    wayland_requested = wants_wayland(config_settings)
    if wayland_requested is not False:
        try:
            from libqtile.backend.wayland.cffi.build import ffi_compile

            ffi_compile(verbose=bool(wayland_requested))
        except Exception as e:
            if wayland_requested:
                sys.exit(f"Wayland backend requested but backend could not be built: {e}")
            else:
                print(f"Wayland backend was not built: {e}")
    else:
        print("Wayland backend disabled")

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
