import os

import pytest

import libqtile.bar
import libqtile.config
import libqtile.confreader
import libqtile.layout


@pytest.fixture(scope='function')
def fake_bar():
    from libqtile.bar import Bar
    height = 24
    b = Bar([], height)
    b.height = height
    return b


TEST_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(os.path.dirname(TEST_DIR), 'data')


@pytest.fixture(scope='module')
def svg_img_as_pypath():
    "Return the py.path object of a svg image"
    import py
    audio_volume_muted = os.path.join(
        DATA_DIR, 'svg', 'audio-volume-muted.svg',
    )
    audio_volume_muted = py.path.local(audio_volume_muted)
    return audio_volume_muted


@pytest.fixture(scope='module')
def fake_qtile():
    import asyncio

    def no_op(*args, **kwargs):
        pass

    class FakeQtile:
        def __init__(self):
            self.register_widget = no_op

        # Widgets call call_soon(asyncio.create_task, self._config_async)
        # at _configure. The coroutine needs to be run in a loop to suppress
        # warnings
        def call_soon(self, func, *args):
            coroutines = [arg for arg in args if asyncio.iscoroutine(arg)]
            if coroutines:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                for func in coroutines:
                    loop.run_until_complete(func)
                loop.close()

    return FakeQtile()


# Fixture that defines a minimal configurations for testing widgets.
# When used in a test, the function needs to receive a list of screens
# (including bar and widgets) as an argument. This config can then be
# passed to the manager to start.
@pytest.fixture(scope='function')
def minimal_conf_noscreen():
    class MinimalConf(libqtile.confreader.Config):
        auto_fullscreen = False
        keys = []
        mouse = []
        groups = [libqtile.config.Group("a"), libqtile.config.Group("b")]
        layouts = [libqtile.layout.stack.Stack(num_stacks=1)]
        floating_layout = libqtile.resources.default_config.floating_layout
        screens = []

    return MinimalConf
