# Copyright (c) 2025 elParaguayo
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
import sys

from setuptools import build_meta as _orig
from setuptools.build_meta import *  # noqa: F401,F403

WAYLAND_DEPENDENCIES = ["pywlroots>=0.17.0,<0.18.0"]
WAYLAND_FFI_BUILD = "./libqtile/backend/wayland/cffi/build.py"


def wants_wayland(config_settings):
    if config_settings:
        for key in ["Backend", "backend"]:
            if config_settings.get(key, "").lower() == "wayland":
                return True

    return False


def get_requires_for_build_wheel(config_settings=None):
    """Inject pywlroots into build dependencies if wayland requested."""
    reqs = _orig.get_requires_for_build_wheel(config_settings)
    if wants_wayland(config_settings):
        reqs += WAYLAND_DEPENDENCIES

    return reqs


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
