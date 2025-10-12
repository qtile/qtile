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

import subprocess
from pathlib import Path

from setuptools import Distribution, Extension
from setuptools import build_meta as _orig

WAYLAND_DIR = Path("libqtile/backend/wayland")

WAYLAND_BACKEND_DIR = WAYLAND_DIR / "qw"
WAYLAND_EXT_DIR = WAYLAND_DIR / "ext"

QW_PROTO_OUT_PATH = WAYLAND_BACKEND_DIR / "proto"
WAYLAND_FFI_BUILD = WAYLAND_DIR / "cffi/build.py"


def generate_build_config(config_settings: dict[str, str]) -> None:
    with open("libqtile/_build_config.py", "w") as f:
        f.write("# This file is generated at build time by builder.py\n")
        for lib in ["PANGO", "PANGOCAIRO", "GOBJECT", "XCBCURSOR"]:
            p = lib + "_PATH"
            f.write(f"{p} = {config_settings.get(p)!r}\n")


def pkg_config_lookup_var(lib, varname) -> str:
    full_cmd = ["pkg-config", lib, f"--variable={varname}"]
    # print the command for transparency
    print(" ".join(full_cmd))
    return subprocess.check_output(full_cmd).decode().strip()


def pkg_config_flags(*libraries: str):
    include_dirs = []
    library_dirs = []

    for libname in libraries:
        library_dirs.append(pkg_config_lookup_var(libname, "libdir"))

        inc_dir = pkg_config_lookup_var(libname, "includedir")

        if (subdir := Path(inc_dir) / libname).exists():
            inc_dir = subdir

        include_dirs.append(inc_dir)

    libs = [lib.removeprefix("lib") for lib in libraries]
    return include_dirs, library_dirs, libs


def prepare_extensions():
    includes, libdirs, libs = pkg_config_flags(
        "wlroots-0.19", "wayland-server", "cairo", "pixman-1", "libdrm"
    )

    wayland_backend = Extension(
        "wayland_backend",
        sources=[
            str(filepath)
            for source_dirs in (WAYLAND_BACKEND_DIR, WAYLAND_EXT_DIR)
            for filepath in source_dirs.rglob("*.c")
        ],
        language="c",
        library_dirs=libdirs,
        libraries=list(libs),
        include_dirs=[str(WAYLAND_BACKEND_DIR), str(QW_PROTO_OUT_PATH)] + includes,
        extra_compile_args=["-DWLR_USE_UNSTABLE"],
    )

    return [wayland_backend]


def build_cff_lib(wayland_requested: bool) -> bool:
    try:
        from libqtile.backend.wayland.cffi.build import ffi_compile

        ffi_compile(verbose=wayland_requested)
    except Exception as e:
        print("Wayland backend was not built:", e)
        return False

    return True


def build_wayland_backend_extension() -> bool:
    dist = Distribution()
    dist.verbose = True
    try:
        dist.ext_modules = prepare_extensions()
    except Exception as e:
        print("Wayland backend extension cannot be build:", e)

    print("Building Wayland backend extension")

    try:
        from setuptools.command.build_ext import build_ext

        cmd = build_ext(dist)
        cmd.build_lib = WAYLAND_DIR
        cmd.ensure_finalized()
        cmd.run()

    except Exception as e:
        print("Wayland backend extension failed to build:", e)
        return False

    return True


def build_wheel(wheel_directory, config_settings=None, metadata_directory=None):
    if config_settings is None:
        config_settings = {}

    from setuptools.command.build_ext import build_ext

    generate_build_config(config_settings or {})
    build_cff_lib(config_settings.get("backend") == "wayland")

    dist = Distribution()
    dist.ext_modules = prepare_extensions()

    print("Building Wayland backend extension")

    cmd = build_ext(dist)
    cmd.build_lib = WAYLAND_DIR
    cmd.ensure_finalized()
    cmd.run()

    return _orig.build_wheel(wheel_directory, config_settings, metadata_directory)


def build_editable(wheel_directory, config_settings=None, metadata_directory=None):
    return build_wheel(wheel_directory, config_settings, metadata_directory)
