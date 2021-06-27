import contextlib
import os

import pytest

from libqtile.backend.wayland.core import Core

wlr_env = {
    "WLR_BACKENDS": "headless",
    "WLR_LIBINPUT_NO_DEVICES": "1",
    "WLR_RENDERER_ALLOW_SOFTWARE": "1",
    "WLR_RENDERER": "pixman",
}


@contextlib.contextmanager
def wayland_environment(outputs):
    """This backend just needs some environmental variables set"""
    old_env = os.environ.copy()
    os.environ.update(wlr_env)
    os.environ["WLR_HEADLESS_OUTPUTS"] = str(outputs)
    yield os.environ
    os.environ = old_env
