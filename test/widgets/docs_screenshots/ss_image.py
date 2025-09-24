from os import path

import pytest

from libqtile.widget import Image

TEST_DIR = path.dirname(path.abspath(__file__))
DATA_DIR = path.join(TEST_DIR, "..", "..", "scripts")
IMAGE_FILE = path.join(DATA_DIR, "qtile-logo-blue.svg")


@pytest.fixture
def widget():
    yield Image


@pytest.mark.parametrize(
    "screenshot_manager",
    [
        {"filename": IMAGE_FILE},
        {"filename": IMAGE_FILE, "margin": 5},
        {"filename": IMAGE_FILE, "rotate": 45},
    ],
    indirect=True,
)
def ss_image(screenshot_manager):
    screenshot_manager.take_screenshot()
