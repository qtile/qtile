FROM fedora:44

RUN dnf install -y \
    cairo-devel \
    cairo-gobject-devel \
    dbus-x11 \
    gcc git make\
    gdb \
    gobject-introspection \
    gtk3 \
    ImageMagick \
    libnotify \
    pango \
    pulseaudio-libs \
    python3.12 python3.12-devel \
    python3.13 python3.13-devel \
    python3.14 python3.14-devel \
    wayland-devel \
    wayland-protocols-devel \
    wlroots-0.20.0-1.fc44 \
    wlroots-devel-0.20.0-1.fc44 \
    xcb-util-cursor \
    xorg-x11-server-Xorg \
    xorg-x11-server-Xephyr \
    xorg-x11-server-Xvfb \
    xorg-x11-server-Xwayland \
    xterm \
    zstd \
    && dnf clean all

RUN curl -LsSf https://astral.sh/uv/install.sh | env UV_INSTALL_DIR=/usr/local/bin sh

WORKDIR /workspace

ENTRYPOINT ["/workspace/scripts/ci-entrypoint"]
