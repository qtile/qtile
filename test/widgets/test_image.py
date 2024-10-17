# Copyright (c) 2021 elParaguayo
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

# Widget specific tests

from os import path

import pytest

import libqtile.bar
import libqtile.config
from libqtile import widget

TEST_DIR = path.dirname(path.abspath(__file__))
DATA_DIR = path.join(TEST_DIR, "..", "data", "png")
IMAGE_FILE = path.join(DATA_DIR, "audio-volume-muted.png")


img = widget.Image(filename=IMAGE_FILE)

parameters = [
    (libqtile.config.Screen(top=libqtile.bar.Bar([img], 40)), "top", "height"),
    (libqtile.config.Screen(left=libqtile.bar.Bar([img], 40)), "left", "width"),
]


@pytest.mark.parametrize("screen,location,attribute", parameters)
def test_default_settings(manager_nospawn, minimal_conf_noscreen, screen, location, attribute):
    config = minimal_conf_noscreen
    config.screens = [screen]

    manager_nospawn.start(config)
    bar = manager_nospawn.c.bar[location]

    info = bar.info()
    for dimension in ["height", "width"]:
        assert info["widgets"][0][dimension] == info[attribute]


no_img = widget.Image()

parameters = [
    (libqtile.config.Screen(top=libqtile.bar.Bar([no_img], 40)), "top", "width"),
    (libqtile.config.Screen(left=libqtile.bar.Bar([no_img], 40)), "left", "height"),
]


@pytest.mark.parametrize("screen,location,attribute", parameters)
def test_no_filename(manager_nospawn, minimal_conf_noscreen, screen, location, attribute):
    config = minimal_conf_noscreen
    config.screens = [screen]

    manager_nospawn.start(config)
    bar = manager_nospawn.c.bar[location]

    info = bar.info()
    assert info["widgets"][0][attribute] == 0


def test_missing_file(manager_nospawn, minimal_conf_noscreen):
    img2 = widget.Image(filename="/this/file/does/not/exist")

    config = minimal_conf_noscreen
    config.screens = [libqtile.config.Screen(top=libqtile.bar.Bar([img2], 40))]

    manager_nospawn.start(config)
    bar = manager_nospawn.c.bar["top"]

    info = bar.info()
    assert info["widgets"][0]["width"] == 0


def test_no_scale(manager_nospawn, minimal_conf_noscreen):
    img2 = widget.Image(filename=IMAGE_FILE, scale=False)

    config = minimal_conf_noscreen
    config.screens = [libqtile.config.Screen(top=libqtile.bar.Bar([img2], 40))]

    manager_nospawn.start(config)
    bar = manager_nospawn.c.bar["top"]

    info = bar.info()
    assert info["widgets"][0]["width"] == 24


def test_no_image(manager_nospawn, minimal_conf_noscreen, logger):
    img = widget.Image()

    config = minimal_conf_noscreen
    config.screens = [libqtile.config.Screen(top=libqtile.bar.Bar([img], 40))]

    manager_nospawn.start(config)

    assert "Image filename not set!" in logger.text


def test_invalid_path(manager_nospawn, minimal_conf_noscreen, logger):
    filename = "/made/up/file.png"
    img = widget.Image(filename=filename)

    config = minimal_conf_noscreen
    config.screens = [libqtile.config.Screen(top=libqtile.bar.Bar([img], 40))]

    manager_nospawn.start(config)

    assert f"Image does not exist: {filename}" in logger.text
