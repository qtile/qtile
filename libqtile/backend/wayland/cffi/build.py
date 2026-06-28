import argparse
import glob
import os
import shutil
import subprocess
import sys
from contextlib import chdir
from dataclasses import dataclass, field
from pathlib import Path

from cffi import FFI
from setuptools import Distribution
from setuptools.command.build_ext import build_ext

# Path resolution

QW_PATH = (Path(__file__).parent / ".." / "qw").resolve()
QW_PROTO_IN_PATH = (QW_PATH / ".." / "proto").resolve()
QW_PROTO_OUT_PATH = QW_PATH / "proto"

TEST_CLIENT_PATH = (
    Path(__file__) / ".." / ".." / ".." / ".." / ".." / "test" / "wayland_clients"
).resolve()
TEST_CLIENT_SRC_PATH = TEST_CLIENT_PATH / "src"
TEST_CLIENT_OUT_PATH = TEST_CLIENT_PATH / "bin"
CLIENT_BASE = TEST_CLIENT_SRC_PATH / "client-base.c"

# Tool resolution

PKG_CONFIG = os.environ.get("PKG_CONFIG", "pkg-config")


def _resolve_wayland_scanner() -> str:
    if explicit := os.environ.get("QTILE_WAYLAND_SCANNER"):
        return explicit
    if found := shutil.which("wayland-scanner"):
        return found
    print(
        "wayland-scanner not found in $PATH or $QTILE_WAYLAND_SCANNER; "
        "falling back to pkg-config",
        file=sys.stderr,
    )
    result = subprocess.run(
        [PKG_CONFIG, "--variable=wayland_scanner", "wayland-scanner"],
        text=True,
        stdout=subprocess.PIPE,
    ).stdout.strip()

    return result


def _pkg_variable(package: str, variable: str) -> str:
    return subprocess.run(
        [PKG_CONFIG, f"--variable={variable}", package],
        text=True,
        stdout=subprocess.PIPE,
        check=True,
    ).stdout.strip()


WAYLAND_SCANNER: str = _resolve_wayland_scanner()
WAYLAND_PROTOCOLS: str = _pkg_variable("wayland-protocols", "pkgdatadir")
WLROOTS_PATH: str = os.getenv("QTILE_WLROOTS_PATH", "/usr/include/wlroots-0.20")

# Protocol and test-client declarations


@dataclass(frozen=True)
class Protocol:
    xml_path: str
    build_server: bool = True
    build_client: bool = False

    @property
    def stem(self) -> str:
        return Path(self.xml_path).stem

    @property
    def private_code(self) -> str:
        return f"{self.stem}-protocol.c"

    @property
    def server_header(self) -> str:
        return f"{self.stem}-protocol.h"

    @property
    def client_header(self) -> str:
        return f"{self.stem}-client-protocol.h"


@dataclass(frozen=True)
class TestClient:
    name: str
    sources: list[str | Path]
    includes: list[str | Path] = field(default_factory=list)
    packages: list[str] = field(default_factory=list)
    extra_args: list[str] = field(default_factory=list)

    @property
    def all_packages(self) -> list[str]:
        return ["wayland-client"] + self.packages


PROTOS: list[Protocol] = [
    Protocol(f"{QW_PROTO_IN_PATH}/wlr-layer-shell-unstable-v1.xml", build_client=True),
    Protocol(
        f"{QW_PROTO_IN_PATH}/wlr-output-power-management-unstable-v1.xml", build_client=True
    ),
    Protocol(f"{WAYLAND_PROTOCOLS}/stable/xdg-shell/xdg-shell.xml", build_client=True),
    Protocol(
        f"{WAYLAND_PROTOCOLS}/unstable/pointer-constraints/pointer-constraints-unstable-v1.xml"
    ),
    Protocol(f"{WAYLAND_PROTOCOLS}/staging/cursor-shape/cursor-shape-v1.xml", build_client=True),
    Protocol(
        f"{WAYLAND_PROTOCOLS}/staging/ext-idle-notify/ext-idle-notify-v1.xml",
        build_client=True,
        build_server=False,
    ),
    Protocol(
        f"{WAYLAND_PROTOCOLS}/unstable/idle-inhibit/idle-inhibit-unstable-v1.xml",
        build_client=True,
        build_server=False,
    ),
    Protocol(
        f"{WAYLAND_PROTOCOLS}/staging/ext-session-lock/ext-session-lock-v1.xml",
        build_client=True,
        build_server=False,
    ),
    Protocol(
        f"{QW_PROTO_IN_PATH}/wlr-foreign-toplevel-management-unstable-v1.xml",
        build_client=True,
        build_server=False,
    ),
    Protocol(
        f"{WAYLAND_PROTOCOLS}/stable/tablet/tablet-v2.xml", build_client=True, build_server=False
    ),
]

TEST_CLIENTS: list[TestClient] = [
    TestClient(
        name="idle-client",
        sources=[
            TEST_CLIENT_SRC_PATH / "idle-client.c",
            CLIENT_BASE,
            QW_PROTO_OUT_PATH / "ext-idle-notify-v1-protocol.c",
            QW_PROTO_OUT_PATH / "idle-inhibit-unstable-v1-protocol.c",
        ],
        includes=[QW_PROTO_OUT_PATH, TEST_CLIENT_SRC_PATH],
    ),
    TestClient(
        name="session-lock",
        sources=[
            TEST_CLIENT_SRC_PATH / "session-lock.c",
            CLIENT_BASE,
            QW_PROTO_OUT_PATH / "ext-session-lock-v1-protocol.c",
        ],
        includes=[QW_PROTO_OUT_PATH, TEST_CLIENT_SRC_PATH],
    ),
    TestClient(
        name="output-power-management",
        sources=[
            TEST_CLIENT_SRC_PATH / "output-power-management.c",
            CLIENT_BASE,
            QW_PROTO_OUT_PATH / "wlr-output-power-management-unstable-v1-protocol.c",
        ],
        includes=[QW_PROTO_OUT_PATH, TEST_CLIENT_SRC_PATH],
    ),
    TestClient(
        name="ftl-manager",
        sources=[
            TEST_CLIENT_SRC_PATH / "ftl-manager.c",
            CLIENT_BASE,
            QW_PROTO_OUT_PATH / "wlr-foreign-toplevel-management-unstable-v1-protocol.c",
        ],
        includes=[QW_PROTO_OUT_PATH, TEST_CLIENT_SRC_PATH],
    ),
    TestClient(
        name="cursor-shape",
        sources=[
            TEST_CLIENT_SRC_PATH / "cursor-shape.c",
            CLIENT_BASE,
            QW_PROTO_OUT_PATH / "cursor-shape-v1-protocol.c",
            QW_PROTO_OUT_PATH / "xdg-shell-protocol.c",
            QW_PROTO_OUT_PATH / "tablet-v2-protocol.c",
        ],
        includes=[QW_PROTO_OUT_PATH, TEST_CLIENT_SRC_PATH],
    ),
    TestClient(
        name="layer-shell",
        sources=[
            TEST_CLIENT_SRC_PATH / "layer-shell.c",
            CLIENT_BASE,
            QW_PROTO_OUT_PATH / "wlr-layer-shell-unstable-v1-protocol.c",
            QW_PROTO_OUT_PATH / "xdg-shell-protocol.c",
        ],
        includes=[QW_PROTO_OUT_PATH, TEST_CLIENT_SRC_PATH],
    ),
]

# Build configuration

CDEF_FILES = [
    "log.h",
    "session-lock.h",
    "server.h",
    "view.h",
    "util.h",
    "output.h",
    "internal-view.h",
    "cursor.h",
    "input-device.h",
    "keyboard.h",
]
XWAYLAND_ONLY_SOURCES = ["xwayland-view.c"]


def wlroots_has_xwayland() -> bool:
    config = Path(WLROOTS_PATH) / "wlr" / "config.h"
    return "WLR_HAS_XWAYLAND 1" in config.read_text()


@dataclass(frozen=True)
class BuildConfig:
    has_xwayland: bool
    include_dirs: list[str]
    libraries: list[str]
    macros: list[tuple[str, str | None]]
    source_files: list[str]

    @classmethod
    def from_environment(cls) -> "BuildConfig":
        has_xwayland = wlroots_has_xwayland()
        source_files = glob.glob(f"{QW_PATH}/*.c")
        if not has_xwayland:
            source_files = [
                f for f in source_files if not any(x in f for x in XWAYLAND_ONLY_SOURCES)
            ]
        macros: list[tuple[str, str | None]] = [("WLR_USE_UNSTABLE", None)]
        if not has_xwayland:
            macros.append(("WLR_HAS_XWAYLAND", "0"))
        return cls(
            has_xwayland=has_xwayland,
            include_dirs=[
                os.getenv("QTILE_CAIRO_PATH", "/usr/include/cairo"),
                os.getenv("QTILE_PIXMAN_PATH", "/usr/include/pixman-1"),
                os.getenv("QTILE_LIBDRM_PATH", "/usr/include/libdrm"),
                WLROOTS_PATH,
                str(QW_PATH),
                str(QW_PROTO_OUT_PATH),
            ],
            libraries=["wlroots-0.20", "wayland-server", "input", "cairo"],
            source_files=source_files,
            macros=macros,
        )

    @property
    def objects(self) -> list[Path]:
        return [
            Path(src).parent / "build" / Path(src).with_suffix(".o").name
            for src in self.source_files
        ]


# CDEF construction

_CDEF_PREAMBLE = """
// logging
enum wlr_log_importance {
    WLR_SILENT,
    WLR_ERROR,
    WLR_INFO,
    WLR_DEBUG,
    ...
};
enum wlr_log_importance wlr_log_get_verbosity(void);
extern "Python" void log_cb(enum wlr_log_importance importance,
                                       const char *log_str);

enum wlr_input_device_type {
    WLR_INPUT_DEVICE_KEYBOARD,
    WLR_INPUT_DEVICE_POINTER,
    WLR_INPUT_DEVICE_TOUCH,
    WLR_INPUT_DEVICE_TABLET,
    WLR_INPUT_DEVICE_TABLET_PAD,
    WLR_INPUT_DEVICE_SWITCH,
};

enum libinput_config_accel_profile {
    LIBINPUT_CONFIG_ACCEL_PROFILE_NONE = 0,
    LIBINPUT_CONFIG_ACCEL_PROFILE_FLAT = (1 << 0),
    LIBINPUT_CONFIG_ACCEL_PROFILE_ADAPTIVE = (1 << 1),
};

enum libinput_config_click_method {
        LIBINPUT_CONFIG_CLICK_METHOD_NONE = 0,
        LIBINPUT_CONFIG_CLICK_METHOD_BUTTON_AREAS = (1 << 0),
        LIBINPUT_CONFIG_CLICK_METHOD_CLICKFINGER = (1 << 1),
};

enum libinput_config_tap_button_map {
        LIBINPUT_CONFIG_TAP_MAP_LRM,
        LIBINPUT_CONFIG_TAP_MAP_LMR,
};

enum libinput_config_scroll_method {
        LIBINPUT_CONFIG_SCROLL_NO_SCROLL = 0,
        LIBINPUT_CONFIG_SCROLL_2FG = (1 << 0),
        LIBINPUT_CONFIG_SCROLL_EDGE = (1 << 1),
        LIBINPUT_CONFIG_SCROLL_ON_BUTTON_DOWN = (1 << 2),
};

struct wlr_box {
	int x, y;
	int width, height;
};

struct wlr_cursor {
    struct wlr_cursor_state *state;
    double x, y;
    ...;
};

struct wlr_output {
	char *name;
	char *make;
	char *model;
	char *serial;
	...;
};

// main callbacks
typedef uint32_t xkb_keysym_t;
typedef struct _cairo_surface cairo_surface_t;
extern "Python" void view_activation_cb(struct qw_view *view, void *userdata);
extern "Python" int keyboard_key_cb(xkb_keysym_t, uint32_t, void *userdata);
extern "Python" void manage_view_cb(struct qw_view *view, void *userdata);
extern "Python" void unmanage_view_cb(struct qw_view *view, void *userdata);
extern "Python" void cursor_motion_cb(void *userdata);
extern "Python" int cursor_button_cb(int button, uint32_t mask, bool pressed, int x, int y, void *userdata);
extern "Python" void pointer_internal_event_cb(int wid, int sx, int sy, int event_type, void *userdata);
extern "Python" void on_screen_change_cb(void *userdata);
extern "Python" void on_screen_reserve_space_cb(struct qw_output *output, void *userdata);
extern "Python" void on_input_device_added_cb(void *userdata);
extern "Python" bool focus_current_window_cb(void *userdata);
extern "Python" void on_session_lock_cb(bool locked, void *userdata);
extern "Python" struct wlr_box get_current_output_dims_cb(void *userdata);
extern "Python" bool add_idle_inhibitor_cb(void *userdata, void *inhibitor, void *view, bool is_layer_surface, bool is_session_lock_surface);
extern "Python" bool remove_idle_inhibitor_cb(void *userdata, void *inhibitor);
extern "Python" bool check_inhibited_cb(void *userdata);
extern "Python" struct qw_qtile_config *get_qtile_config_cb(void *userdata);
extern "Python" void idle_state_change_cb(void *userdata, int seconds, bool is_idle);

extern "Python" int request_focus_cb(void *userdata);
extern "Python" int request_close_cb(void *userdata);
extern "Python" int request_fullscreen_cb(bool fullscreen, void *userdata);
extern "Python" int request_maximize_cb(bool maximize, void *userdata);
extern "Python" int request_minimize_cb(bool minimize, void *userdata);
extern "Python" void set_title_cb(char* title, void *userdata);
extern "Python" void set_app_id_cb(char* app_id, void *userdata);
"""


def _build_cdef(config: BuildConfig) -> str:
    """Read QW headers and concatenate into a single CFFI cdef string."""
    parts = [_CDEF_PREAMBLE]
    for filename in CDEF_FILES:
        parts.append(_read_header(QW_PATH / filename, config.has_xwayland))
    return "".join(parts)


def _read_header(path: Path, has_xwayland: bool) -> str:
    """
    Read a single header, stripping preprocessor directives and
    xwayland-only blocks when xwayland is not available.
    """
    lines: list[str] = []
    in_private_data = False
    skip_xwayland_block = False

    for line in path.read_text().splitlines(keepends=True):
        stripped = line.strip()
        if stripped.startswith("#if"):
            if "WLR_HAS_XWAYLAND" in stripped and not has_xwayland:
                skip_xwayland_block = True
            continue
        if stripped.startswith("#else") and skip_xwayland_block:
            skip_xwayland_block = False
            continue
        if stripped.startswith("#endif") and skip_xwayland_block:
            skip_xwayland_block = False
            continue
        if skip_xwayland_block or line.startswith("#"):
            continue
        if stripped.lower().startswith("// private data"):
            in_private_data = True
            lines.append("    ...;\n")
            continue
        if line.startswith("};") and in_private_data:
            in_private_data = False
        if not in_private_data:
            lines.append(line)

    return "".join(lines)


# Build steps


def generate_protocols() -> None:
    QW_PROTO_OUT_PATH.mkdir(exist_ok=True)
    for proto in PROTOS:
        _generate_protocol(proto)


def _generate_protocol(proto: Protocol) -> None:
    if proto.build_server:
        _run_scanner("server-header", proto.xml_path, QW_PROTO_OUT_PATH / proto.server_header)
    if proto.build_client:
        _run_scanner("client-header", proto.xml_path, QW_PROTO_OUT_PATH / proto.client_header)
        _run_scanner("private-code", proto.xml_path, QW_PROTO_OUT_PATH / proto.private_code)


def _run_scanner(mode: str, xml_path: str, output: Path) -> None:
    subprocess.run([WAYLAND_SCANNER, mode, xml_path, output.resolve().as_posix()], check=True)


def build_c_objects(config: BuildConfig, *, debug: bool = False, asan: bool = False) -> None:
    with chdir(QW_PATH):
        dist = Distribution()
        cmd = build_ext(dist)
        cmd.setup_shlib_compiler()

        preargs = ["-g3", "-Og"] if (debug or asan) else ["-O2"]
        preargs += ["-fPIC", "-Wall", "-Wextra"]

        cmd.shlib_compiler.compile(
            [os.path.basename(p) for p in config.source_files],
            output_dir="build",
            macros=config.macros,
            include_dirs=config.include_dirs,
            extra_preargs=preargs,
        )


def build_test_clients() -> None:
    TEST_CLIENT_OUT_PATH.mkdir(parents=True, exist_ok=True)
    for client in TEST_CLIENTS:
        _build_test_client(client)


def _build_test_client(client: TestClient) -> None:
    def to_str(v: str | Path) -> str:
        return v.resolve().as_posix() if isinstance(v, Path) else v

    cflags = (
        subprocess.check_output(["pkg-config", "--cflags", *client.all_packages]).decode().split()
    )
    libs = (
        subprocess.check_output(["pkg-config", "--libs", *client.all_packages]).decode().split()
    )

    cmd = [
        "cc",
        *cflags,
        *(to_str(s) for s in client.sources),
        *(arg for inc in client.includes for arg in ("-I", to_str(inc))),
        *client.extra_args,
        *libs,
        "-o",
        (TEST_CLIENT_OUT_PATH / client.name).resolve().as_posix(),
    ]
    subprocess.run(cmd, check=True)


def compile_ffi(
    config: BuildConfig, *, verbose: bool = False, debug: bool = False, asan: bool = False
) -> None:
    extra_compile_args: list[str] = []
    extra_link_args: list[str] = []
    if debug or asan:
        extra_compile_args += ["-g3", "-Og"]
    if asan:
        extra_compile_args += ["-fsanitize=address,leak,undefined", "-fno-omit-frame-pointer"]
        extra_link_args += ["-fsanitize=address,undefined"]

    source = "\n".join(f'#include "{h}"' for h in CDEF_FILES) + "\n"

    ffi = FFI()
    ffi.set_source(
        "libqtile.backend.wayland._ffi",
        source,
        define_macros=config.macros,
        include_dirs=config.include_dirs,
        extra_objects=[str(o) for o in config.objects],
        libraries=config.libraries,
        extra_compile_args=extra_compile_args,
        extra_link_args=extra_link_args,
    )
    ffi.cdef(_build_cdef(config))
    ffi.compile(
        tmpdir=Path(__file__).parent.parent.parent.parent.parent.as_posix(),
        verbose=verbose,
    )


# Top-level entry point


def ffi_compile(*, verbose: bool = False, debug: bool = False, asan: bool = False) -> None:
    config = BuildConfig.from_environment()
    generate_protocols()
    build_c_objects(config, debug=debug, asan=asan)
    compile_ffi(config, verbose=verbose, debug=debug, asan=asan)
    build_test_clients()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Qtile wayland backend build script.")
    parser.add_argument("--debug", action="store_true", help="Add debugging symbols.")
    parser.add_argument(
        "--asan", action="store_true", help="Compile with address sanitisation support."
    )
    args = parser.parse_args()
    ffi_compile(debug=args.debug, asan=args.asan)
