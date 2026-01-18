import pytest

from test.widgets.test_do_not_disturb import patched_dnd  # noqa: F401


@pytest.fixture
def widget(patched_dnd):  # noqa: F811
    class DoNotDisturb(patched_dnd):
        pass

    yield DoNotDisturb


def ss_do_not_disturb(screenshot_manager):
    screenshot_manager.take_screenshot()
