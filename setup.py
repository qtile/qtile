import os
import subprocess

from pathlib import Path
from setuptools import Extension, setup
from typing import Iterator

WAYLAND_BACKEND_DIR = Path("libqtile/backend/wayland/qw")
WAYLAND_EXTENSION_DIR = Path("libqtile/backend/wayland/ext")
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


def log_subproc_calls(func):
    def wrapped(cmd, *args, **kwargs):
        print("$", " ".join(cmd))
        return func(cmd, *args, **kwargs)

    return wrapped

subprocess.check_output = log_subproc_calls(subprocess.check_output)


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


includes, libdirs, libs = pkg_config_flags(
    "wlroots-0.19",
    "wayland-server",
    "cairo",
    "pixman-1",
    "libdrm"
)


print(os.getenv("QTILE_CAIRO_PATH", "/usr/include/cairo"))
wayland_backend = Extension(
    "wayland_backend",
    sources=[
        *find_sources(WAYLAND_BACKEND_DIR),
        *find_sources(WAYLAND_EXTENSION_DIR)
    ],
    language="c",
    library_dirs=libdirs,
    libraries=libs,
    include_dirs=[str(WAYLAND_BACKEND_DIR), str(QW_PROTO_OUT_PATH)] + includes,
    extra_compile_args=["-DWLR_USE_UNSTABLE"]
)

if __name__ == "__main__":
    setup(ext_modules=[wayland_backend])
