# Copyright (c) 2020 Matt Colligan
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

import os
import tempfile

import pytest
from xcffib.testing import XvfbTest

from resources import default_config
from test.conftest import can_connect_x11, Xephyr, BareConfig, TestManager
from test.test_manager import ManagerConfig

manager_config_highdpi = pytest.mark.parametrize("manager_highdpi", [ManagerConfig], indirect=True)


@manager_config_highdpi
def test_high_dpi_window_size(manager_highdpi):
    manager_highdpi.test_xclock()
    assert manager_highdpi.c.screen.info()["width"] == 2876
    assert manager_highdpi.c.screen.info()["height"] == 1200
    assert manager_highdpi.c.window.info()["width"] == 164 * 2
    assert manager_highdpi.c.window.info()["height"] == 164 * 2


@pytest.fixture(scope="function")
def manager_highdpi(request):
    os.environ["QTILE_DPI"] = "150"
    config = getattr(request, "param", BareConfig)

    for attr in dir(default_config):
        if not hasattr(config, attr):
            setattr(config, attr, getattr(default_config, attr))

    with tempfile.NamedTemporaryFile() as f:
        sockfile = f.name
        try:
            with HighDpiXvfbTest() as fb:
                display = os.environ["DISPLAY"]
                if not can_connect_x11(display):
                    raise OSError("Xvfb did not come up")

                with Xephyr(width=2876, height=1200, dpi=150) as x:
                    manager = TestManager(sockfile, display, request.config.getoption("--debuglog"))
                    manager.start(config)

                    yield manager
        finally:
            del os.environ["QTILE_DPI"]
            manager.terminate()


class HighDpiXvfbTest(XvfbTest):

    def __init__(self, width=2876, height=1200, depth=16, dpi=150):
        super().__init__(width, height, depth)
        self.dpi = dpi

    def _xvfb_command(self):
        """
        we need to start the xvfb like so: /usr/bin/Xvfb :99 -screen 0 2000x2000x24 -dpi 200
          original 1440 X 600 x 16 | in millimeters 487 x 203 | in inch 19.1732387 x 7.9921302999999995 => dpi 75
          highdpi 2876 x 1200 Pixel | = 487 x 203.2 mm | = 150 dpi
        """
        screen = '%sx%sx%s' % (self.width, self.height, self.depth)
        return ['Xvfb', os.environ['DISPLAY'], '-screen', '0', screen, '-dpi', str(self.dpi)]

