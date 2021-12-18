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
import json
import os
import shutil
from functools import partial
from pathlib import Path

import cairocffi
import pytest

from libqtile.bar import Bar
from libqtile.config import Group, Screen


@pytest.fixture(scope="session")
def target():
    folder = Path(__file__).parent / "screenshots"
    docs_folder = (
        Path(__file__).parent
        / ".."
        / ".."
        / ".."
        / "docs"
        / "_static"
        / "screenshots"
        / "widgets"
    )
    log = os.path.join(docs_folder, "shots.json")
    if folder.is_dir():
        shutil.rmtree(folder)
    folder.mkdir()
    key = {}

    def get_file_name(w_name, config):
        nonlocal key

        # Convert config into a string of key=value
        entry = ", ".join(f"{k}={repr(v)}" for k, v in config.items())

        # Check if widget is in the key dict
        if w_name not in key:
            key[w_name] = {}

        # Increment the index number
        indexes = [int(x) for x in key[w_name]]
        index = max(indexes) + 1 if indexes else 1

        # Record the config
        key[w_name][index] = entry

        # Define the target folder and check it exists
        shots_dir = os.path.join(folder, w_name)
        if not os.path.isdir(shots_dir):
            os.mkdir(shots_dir)

        # Returnt the path for the screenshot
        return os.path.join(shots_dir, f"{index}.png")

    yield get_file_name

    # We copy the screenshots from the test folder to the docs folder at the end
    # This prevents pytest deleting the files itself

    # Remove old screenshots
    if os.path.isdir(docs_folder):
        shutil.rmtree(docs_folder)

    # Copy to the docs folder
    shutil.copytree(folder, docs_folder)
    with open(log, "w") as f:
        json.dump(key, f)

    # Clear up the tests folder
    shutil.rmtree(folder)


@pytest.fixture
def screenshot_manager(widget, request, manager_nospawn, minimal_conf_noscreen, target):
    """
    Create a manager instance for the screenshots. Individual "tests" should only call
    `screenshot_manager.take_screenshot()` but the destination path is also available in
    `screenshot_manager.target`.

    Widgets should create their own `widget` fixture in the relevant file (applying
    monkeypatching etc as necessary).

    Configs can then be passed by parametrizing "screenshot_manager".
    """
    # Partials are used to hide some aspects of the config from being displayed in the
    # docs. We need to split these out into their constituent parts.
    if type(widget) is partial:
        widget_class = widget.func
        widget_config = widget.keywords
    else:
        widget_class = widget
        widget_config = {}

    class ScreenshotWidget(widget_class):
        def __init__(self, *args, **kwargs):
            widget_class.__init__(self, *args, **kwargs)
            # We need the widget's name to be the name of the inherited class
            self.name = widget_class.__name__.lower()

        def cmd_take_screenshot(self, target):
            if not self.configured:
                return

            # Screenshots only run on X11
            source = self.drawer._xcb_surface

            dest = cairocffi.ImageSurface(cairocffi.FORMAT_ARGB32, self.width, self.height)
            with cairocffi.Context(dest) as ctx:
                ctx.set_source_surface(source)
                ctx.paint()

            dest.write_to_png(target)

    class ScreenshotBar(Bar):
        def cmd_take_screenshot(self, target, x=0, y=0, width=None, height=None):
            """Takes a screenshot of the bar. The area can be selected."""
            if not self._configured:
                return

            if width is None:
                width = self.drawer.width

            if height is None:
                height = self.drawer.height

            # Screenshots only run on X11
            source = "_xcb_surface"

            # Widgets aren't drawn to the bar's drawer so we first need to render them all to a single surface
            bar_copy = cairocffi.ImageSurface(
                cairocffi.FORMAT_ARGB32, self.drawer.width, self.drawer.height
            )
            with cairocffi.Context(bar_copy) as ctx:
                ctx.set_source_surface(getattr(self.drawer, source))
                ctx.paint()

                for i in self.widgets:
                    ctx.set_source_surface(getattr(i.drawer, source), i.offsetx, i.offsety)
                    ctx.paint()

            # Then we copy the desired area to our destination surface
            dest = cairocffi.ImageSurface(cairocffi.FORMAT_ARGB32, width, height)
            with cairocffi.Context(dest) as ctx:
                ctx.set_source_surface(bar_copy, x=x, y=y)
                ctx.paint()

            dest.write_to_png(target)

    # Get the widget and config
    config = getattr(request, "param", dict())
    wdgt = ScreenshotWidget(**{**widget_config, **config})
    name = wdgt.name

    # Create a function to generate filename
    def filename():
        return target(name, config)

    # Add the widget to our config
    minimal_conf_noscreen.groups = [Group(i) for i in "123456789"]
    minimal_conf_noscreen.fake_screens = [
        Screen(top=ScreenshotBar([wdgt], 32), x=0, y=0, width=300, height=300),
        Screen(top=ScreenshotBar([], 32), x=0, y=300, width=300, height=300),
    ]

    manager_nospawn.start(minimal_conf_noscreen)

    # Add some convenience attributes for taking screenshots
    manager_nospawn.target = filename
    ss_widget = manager_nospawn.c.widget[name]
    manager_nospawn.take_screenshot = lambda f=filename: ss_widget.take_screenshot(f())

    yield manager_nospawn
