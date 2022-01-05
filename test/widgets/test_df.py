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

import sys
from importlib import reload
from types import ModuleType

import pytest

from libqtile.widget import df
from test.widgets.conftest import FakeBar


class FakeOS(ModuleType):
    class statvfs:  # noqa: N801
        def __init__(self, *args, **kwargs):
            pass

        @property
        def f_frsize(self):
            return 4096

        @property
        def f_blocks(self):
            return 60000000

        @property
        def f_bfree(self):
            return 15000000

        @property
        def f_bavail(self):
            return 10000000


# Patches os.stavfs gives these values for df widget:
#  unit: G
#  size = 228
#  free = 57
#  user_free = 38
#  ratio (user_free / size) = 83.3333%
@pytest.fixture()
def patched_df(monkeypatch):
    monkeypatch.setitem(sys.modules, "os", FakeOS("os"))
    reload(df)


@pytest.mark.usefixtures("patched_df")
def test_df_no_warning(fake_qtile, fake_window):
    """Test no text when free space over threshold"""
    df1 = df.DF()
    fakebar = FakeBar([df1], window=fake_window)
    df1._configure(fake_qtile, fakebar)
    text = df1.poll()
    assert text == ""

    df1.draw()
    assert df1.layout.colour == df1.foreground


@pytest.mark.usefixtures("patched_df")
def test_df_always_visible(fake_qtile, fake_window):
    """Test text is always displayed"""
    df2 = df.DF(visible_on_warn=False)
    fakebar = FakeBar([df2], window=fake_window)
    df2._configure(fake_qtile, fakebar)
    text = df2.poll()

    # See values above
    assert text == "/ (38G|83%)"

    df2.draw()
    assert df2.layout.colour == df2.foreground


@pytest.mark.usefixtures("patched_df")
def test_df_warn_space(fake_qtile, fake_window):
    """
    Test text is visible and colour changes when space
    below threshold
    """
    df3 = df.DF(warn_space=40)
    fakebar = FakeBar([df3], window=fake_window)
    df3._configure(fake_qtile, fakebar)
    text = df3.poll()

    # See values above
    assert text == "/ (38G|83%)"

    df3.draw()
    assert df3.layout.colour == df3.warn_color
