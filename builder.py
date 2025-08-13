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

import os
import subprocess

from pathlib import Path
from setuptools import Extension, setup
from typing import Iterator

from setuptools import setup
from setuptools import build_meta as _orig
from setuptools.build_meta import *  # noqa: F401,F403

WAYLAND_FFI_BUILD = "./libqtile/backend/wayland/cffi/build.py"

WAYLAND_BACKEND_DIR = Path("libqtile/backend/wayland/qw")
QW_PROTO_OUT_PATH = WAYLAND_BACKEND_DIR / "proto"


def find_sources(basepath: Path) -> Iterator[str]:
    files = (
        (current_dir, file)
        for current_dir, _, files in os.walk(basepath)
        for file in files
    )

    for current_dir, file in files:
        *_, ext = os.path.splitext(file)
        if ext != f"{os.path.extsep}c":
            continue

        fullpath = os.path.join(current_dir, file)
        print(f"Registering {fullpath} to sources")
        yield fullpath


def pkg_config_flags(*packages):
    # todo: improve me
    include_dirs = []
    library_dirs = []
    libraries = []

    for pkg in packages:
        cflags = subprocess.check_output(["pkg-config", "--cflags", pkg]).decode().split()
        libs = subprocess.check_output(["pkg-config", "--libs", pkg]).decode().split()

        include_dirs.extend(f[2:] for f in cflags if f.startswith("-I"))
        library_dirs.extend(l[2:] for l in libs if l.startswith("-L"))
        libraries.extend(l[2:] for l in libs if l.startswith("-l"))

    include_dirs = list(dict.fromkeys(include_dirs))
    library_dirs = list(dict.fromkeys(library_dirs))
    libraries  = list(dict.fromkeys(libraries))

    return include_dirs, library_dirs, libraries



def build_wayland_extension():
    includes, libdirs, libs = pkg_config_flags(
        "wlroots-0.19", "wayland-server", "cairo", "pixman-1", "libdrm"
    )


    wayland_backend = Extension(
        "wayland_backend",
        sources=list(find_sources(WAYLAND_BACKEND_DIR)),
        language="c",
        library_dirs=libdirs,
        libraries=libs,
        include_dirs=[str(WAYLAND_BACKEND_DIR), str(QW_PROTO_OUT_PATH)] + includes,
        extra_compile_args=["-DWLR_USE_UNSTABLE"],
    )

    return wayland_backend


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


# what lies below is sorcery

def hook_sys_modules_ext(*ext):
    sys.modules["__SETUPTOOLS_EXTS__"] = {"ext_modules": exts} # type: ignore 


def _patched_setup(**kwargs):
    exts = sys.modules.pop("__SETUPTOOLS_EXTS__", {}).get("ext_modules", [])
    kwargs.setdefault("ext_modules", exts)

    from setuptools import _orig_setup # type: ignore
    return _orig_setup(**kwargs)


import setuptools
setuptools._orig_setup = setuptools.setup # type: ignore
setuptools.setup = _patched_setup
