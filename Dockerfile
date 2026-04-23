FROM fedora:44

RUN dnf install -y \
    git \
    make gcc gcc-c++ \
    which findutils \
    systemd dbus-devel \
    gobject-introspection-devel \
    gtk3 gtk3-devel \
    libnotify libnotify-devel \
    libgudev libgudev-devel \
    graphviz ImageMagick \
    xorg-x11-server-Xephyr \
    xorg-x11-server-Xvfb \
    dbus-x11 \
    xcb-util-devel \
    xcb-util-image-devel \
    xcb-util-keysyms-devel \
    xcb-util-renderutil-devel \
    xcb-util-wm-devel \
    libxcb-devel \
    libxkbcommon-devel \
    python3-gobject \
    cairo-devel \
    gdk-pixbuf2-devel \
    librsvg2-devel \
    xcb-util-cursor \
    xterm \
    pulseaudio-libs \
    wget tar gzip xz \
    wayland-devel \
    wayland-protocols-devel \
    mesa-libEGL-devel \
    mesa-libgbm-devel \
    mesa-libGLES-devel \
    libglvnd-devel \
    libepoxy-devel \
    libinput-devel \
    libpciaccess-devel \
    xcb-util-errors-devel \
    libXfont2-devel \
    libxshmfence-devel \
    libtirpc-devel \
    xorg-x11-font-utils \
    xorg-x11-server-devel \
    ninja-build meson \
    libdrm-devel \
    pixman-devel \
    hwdata \
    systemd-devel \
    gdb \
    xorg-x11-server-Xwayland \
    seatd \
    wlroots0.19-devel \
    python3.12 python3.12-devel \
    python3.13 python3.13-devel \
    python3.14 python3.14-devel \
    nss_wrapper-libs \
    && dnf clean all

RUN curl -LsSf https://astral.sh/uv/install.sh | env UV_INSTALL_DIR=/usr/local/bin sh

WORKDIR /workspace

ENV PATH="/home/user/.local/bin:$PATH"

ENTRYPOINT ["/workspace/scripts/ci-entrypoint"]
