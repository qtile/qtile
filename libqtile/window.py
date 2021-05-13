# This is a temporary module that redirects imports from `libqtile.window` to
# `libqtile.backend.x11.window` to reduce config breakages due to the removal of
# `libqtile.window`. This can be removed after release.

import warnings

from libqtile.backend.x11.window import *  # noqa: F401,F403

warnings.warn(
    "libqtile.window is deprecated, use libqtile.backend.x11.window",
    DeprecationWarning,
)
