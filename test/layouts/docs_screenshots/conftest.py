# Copyright (c) 2022 elParaguayo
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
import glob
import json
import os
import shutil
from functools import partial
from pathlib import Path
from subprocess import run
from types import MethodType

import pytest

from libqtile.config import Screen
from test.helpers import BareConfig


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
        / "layouts"
    )
    log = os.path.join(docs_folder, "shots.json")
    if folder.is_dir():
        shutil.rmtree(folder)
    folder.mkdir()
    key = {}

    class LayoutAnimator:
        def __init__(self, name, config):
            self.temp_frames = list()
            self.layout_name = name
            self.config = config

            # Define the target folder and check it exists
            self.shots_dir = os.path.join(folder, self.layout_name)
            if not os.path.isdir(self.shots_dir):
                os.mkdir(self.shots_dir)

            self.widcards = os.path.join(self.shots_dir, "shot_*.png")

            self.index = 0

        def get_temp_file_name(self):
            """Returns a path for the screenshot."""
            self.index += 1
            return os.path.join(self.shots_dir, f"shot_{self.index}.png")

        def animate(self):
            """Converts all the frames into an animated gif and removes frames."""
            nonlocal key

            # Convert config into a string of key=value
            entry = ", ".join(f"{k}={repr(v)}" for k, v in self.config.items())

            # Check if widget is in the key dict
            if self.layout_name not in key:
                key[self.layout_name] = {}

            # Increment the index number
            indexes = [int(x) for x in key[self.layout_name]]
            index = max(indexes) + 1 if indexes else 1

            output = os.path.join(self.shots_dir, f"{index}.gif")

            run(["convert", "-delay", "75", self.widcards, "-resize", "300x225", output])

            # Delete frames
            for f in glob.glob(self.widcards):
                os.remove(f)

            # Record the config
            key[self.layout_name][index] = entry

    yield LayoutAnimator

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
def screenshot_manager(layout, request, manager_nospawn, target):
    """
    Create a manager instance for the screenshots. Individual "tests" should only call
    `screenshot_manager.take_screenshot()`. At the end of the test, the screenshots will
    be combined into a single animated gif.

    Layouts should create their own `layout` fixture in the relevant file. Configs can then
    be passed by parametrizing "screenshot_manager".
    """
    # Partials can be used to hide some aspects of the config from being displayed in the
    # docs. We need to split these out into their constituent parts.
    if type(layout) is partial:
        layout_class = layout.func
        layout_config = layout.keywords
    else:
        layout_class = layout
        layout_config = {}

    # Get the layout config from the parameterisation
    config = getattr(request, "param", dict())

    # We need to embed the screenshot call in a CommandObject
    # Calling directly from manager_nospawns captures the mouse pointer
    # Adding the command to the layout causes issues with Slice as commands
    # are rooted to the fallback layout
    class ShootScreen(Screen):
        def cmd_take_screenshot(self, filepath):
            run(["scrot", "-o", filepath])

    # Define a config containing our layout
    class ScreenShotConfig(BareConfig):
        layouts = [layout_class(**{**layout_config, **config})]
        screens = [ShootScreen()]

    # Define a new method to spawn a window with an incremental index number displayed
    def add_window(self):
        self.test_window(
            str(self._window_index), extra_args=["layout_screenshot", str(self._window_index)]
        )
        self._window_index += 1

    # Attach the new method to the manager instance
    manager_nospawn._window_index = 1
    manager_nospawn.add_window = MethodType(add_window, manager_nospawn)

    # Start the manager
    manager_nospawn.start(ScreenShotConfig)

    # Create the animator object
    animator = target(ScreenShotConfig.layouts[0].name, config)

    # Define function to take a screenshot of the layout
    def take_screenshot(self):
        self.c.screen.take_screenshot(animator.get_temp_file_name())

    # Attach it to the manager
    manager_nospawn.take_screenshot = MethodType(take_screenshot, manager_nospawn)

    yield manager_nospawn

    # Take one more screenshot so we get a longer pause at the end of the loop
    manager_nospawn.take_screenshot()

    # Convert the frames into an animated gif
    animator.animate()
